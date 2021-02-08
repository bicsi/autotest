import subprocess
import argparse
import time
import random
import os
import logging
from hyperopt import hp
import hyperopt.fmin
import numpy as np
import datetime
from tqdm import trange

algo = hyperopt.tpe.suggest
COMPILE_COMMAND = ['g++', '-std=c++11', '-O2']
TU_PARAM_REQ = 'TU_PARAM_REQ'
L2_REGULARIZATION = 0.01


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generator", type=str,
                        default='gen.cpp',
                        help="Generator file (default: gen.cpp)")
    parser.add_argument("--solution", type=str,
                        default='sol.cpp',
                        help="Model solution file (default: sol.cpp)")
    parser.add_argument("--tests", type=str,
                        default='tests.txt',
                        help="Tests file (default: tests.txt)")
    parser.add_argument('-n', '--n-iterations', type=int,
                        default=50,
                        help='Number of iterations, a.k.a. calls to generator (default: 10)')
    parser.add_argument('--output-dir',
                        default='out',
                        help='Directory path to place the tests (default: out)')
    parser.add_argument('--in-pattern',
                        default='{name}.in',
                        help='Input file pattern (default: {name}.in)')
    parser.add_argument('--ans-pattern',
                        default='{name}.ok',
                        help='Answer file pattern (default: {name}.ok)')
    return parser.parse_args()


def parse_spec(sexp):
    def rec(pos):
        opos = pos
        if sexp[pos] == '(':
            ans = []
            while sexp[pos] != ')':
                now, pos = rec(pos + 1)
                ans.append(now)
            return ans, pos + 1
        else:
            while pos < len(sexp) and sexp[pos] not in '() ':
                pos += 1
            return sexp[opos:pos], pos
    parse_tree, pos = rec(0)
    assert pos == len(sexp)

    ans = {}
    for [k, v] in parse_tree:
        ans[k] = v
    return ans


def generate_feasible_value(spec):
    if spec['type'] == 'float':
        value = round(random.uniform(
            float(spec['min']), float(spec['max'])), 3)
    elif spec['type'] == 'int':
        value = random.randint(int(spec['min']), int(spec['max']))
    elif spec['type'] == 'choice':
        value = random.choice(spec['choices'])
    else:
        raise ValueError(f"Unrecognized spec type: '{spec['type']}'")
    return value


def run_generator(generator_exec_path, feed_dict, resolve_new_param):
    output = []
    args = [generator_exec_path, '--interactive']
    for name, value in feed_dict.items():
        args.append(f"-P{name}")
        args.append(str(value))
    # logging.debug(f"Running command: {args}")
    with subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE) as process:
        while True:
            line = process.stdout.readline().decode('UTF-8')
            if not line:
                if process.poll() is not None:
                    break
                time.sleep(0.01)
            if line.startswith(TU_PARAM_REQ):
                _, param_name, param_spec = line.split(maxsplit=2)
                param_spec = parse_spec(param_spec.strip())
                logging.debug(f"Found param: {param_name} {param_spec}")
                param_value = resolve_new_param(param_name, param_spec)
                feed_dict[param_name] = param_value
                process.stdin.write(f"{param_value}\n".encode('UTF-8'))
                process.stdin.flush()
            else:
                output.append(line)

        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(
                f'Generator retured non-zero exit code: {return_code}')
    return "".join(output)


def run_solution(solution_exec_path, in_contents):
    with subprocess.Popen(
            [solution_exec_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE) as process:
        stdout, stderr = process.communicate(
            input=in_contents.encode('UTF-8'), timeout=10)
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(
                f"Solution returned non-zero exit code: {return_code}")
        goal_outputs = list(map(float, stderr.decode(
            'UTF-8').strip().splitlines()[-1].split()))
        return stdout.decode('UTF-8'), goal_outputs


def parse_tests_file(tests_file):
    tests = []
    with open(tests_file, 'r') as file:
        header = None
        for line in file:
            tokens = line.split()
            if header is None:
                header = tokens
                assert header[0] == '#'
            else:
                assert len(tokens) == len(header)
                test_dict = {k: v for k, v in zip(header, tokens)}
                tests.append(test_dict)
    return tests


class HyperoptSampler:
    """
    This sample uses the hyperopt package as a backend to sample in the
    parameter space. It has various ugly "hacks" inside the hyperopt library
    to adhere to the scenario of parameters known while optimizing.

    That's because hyperopt uses some (complicated and more or less useless)
    representation that's compatible to NoSQL MongoDB databases.

    This API choice has a lot of shortcomings in my opinion. Anyways, we would like
    to use the hyperopt TPE as a sampler instead of the optimizer, so we have to 
    manually handle their internal data storage.
    """

    def __init__(self):
        # The hyperopt space will be populated as self.remember will be called
        self.space = {}
        # The trials keep track of the past samplings (in dict format)
        self.trials = []
        # This rstate is manually handled as we have a specific training loop.
        self.rstate = np.random.RandomState()

    def sample(self, test_dict):
        # self.space keeps track of the whole parameter space; however,
        # nothing keeps us from fixing some parameters inside this
        # sampling.
        space = {name: dist for name, dist in self.space.items()
                 if name not in test_dict}

        if not space:
            return test_dict.copy()

        trials = self._get_hyperopt_trials_instance(space)
        feed_dict = trials.fmin(lambda _: -1., space, algo,
                                max_evals=len(trials) + 1, show_progressbar=False, rstate=self.rstate)
        feed_dict.update(test_dict)
        # logging.debug(trials.trials)
        return feed_dict

    def _get_hyperopt_trials_instance(self, space):
        """
        Converts dict-like trials to adhere to the 'internal' hyperopt format,
        and populates the hyperopt.Trials object.
        This might seem unnecessarily complicated (and maybe it is),
        but I haven't managed to find a better way.
        """
        trials = hyperopt.Trials()
        # These arrays are needed to create trial docs inside the hyperopt.Trials
        # instance.
        tids, specs, results, miscs = [], [], [], []
        for idx, trial in enumerate(self.trials):
            tids.append(idx)
            specs.append(None)
            results.append(trial['result'])
            # This is to adhere to the hyperopt API.
            misc = {
                'idxs': {},
                'cmd': ('domain_attachment', 'FMinIter_Domain'),
                'workdir': None,
                'vals': {},
            }
            for name in space:
                misc['tid'] = idx
                if name not in trial['vals']:
                    misc['idxs'][name] = []
                    misc['vals'][name] = []
                else:
                    misc['idxs'][name] = [idx]
                    misc['vals'][name] = [trial['vals'][name]]
            miscs.append(misc)

        # Create the documents and populate them with more extra info.
        docs = trials.new_trial_docs(tids, specs, results, miscs)
        for doc in docs:
            # Not setting this state caused trials to be completely
            # re-evaluated.
            doc['state'] = hyperopt.base.JOB_STATE_DONE
            doc['book_time'] = datetime.datetime.now()
            doc['refresh_time'] = datetime.datetime.now()

        # Finally, insert the documents to recover the original db.
        trials.insert_trial_docs(docs)
        trials.refresh()

        return trials

    def resolve_new_param(self, name, spec):
        """
        When a new param is dynamically discovered, we update our parameter
        space with the proper distribution
        """
        if spec['type'] == 'float':
            dist = hp.uniform(name, float(spec['min']), float(spec['max']))
        elif spec['type'] == 'int':
            dist = hp.quniform(name, int(spec['min']), int(spec['max']))
        elif spec['type'] == 'choice':
            dist = hp.choice(name, [(c, c) for c in spec['choices']])
        else:
            raise ValueError(f"Unrecognized type: {spec['type']}")
        self.space[name] = dist
        return generate_feasible_value(spec)

    def remember(self, feed_dict, loss):
        """
        This function will be called once we have evaluated a sample and know
        its loss. In this case, we just append it to our trial records.
        """
        self.trials.append({
            'vals': feed_dict.copy(),
            'result': {
                'status': 'ok',
                'loss': loss,
            }
        })


def generate_test(sampler, test_dict, param_specs, goal_targets, n_iterations):
    solution = None
    tr = trange(n_iterations, desc='GEN')
    for _ in tr:
        feed_dict = sampler.sample(test_dict)
        for param_name, param_value in feed_dict.items():
            if isinstance(param_value, float):
                feed_dict[param_name] = round(param_value, 3)
        # logging.debug(feed_dict)
        # Running the generator also updates feed_dict and param_specs.
        in_contents = run_generator(
            './gen', feed_dict, sampler.resolve_new_param)
        ans_contents, goal_outputs = run_solution('./sol', in_contents)
        assert len(goal_outputs) == len(goal_targets)
        loss, reg_loss = 0, 0
        for i in range(len(goal_targets)):
            loss += abs(goal_targets[i] - goal_outputs[i])
        for p in feed_dict:
            if p not in test_dict and isinstance(feed_dict[p], float):
                reg_loss += L2_REGULARIZATION * feed_dict[p] ** 2
        loss += reg_loss
        if solution is None or solution['loss'] > loss:
            solution = {
                "in": in_contents,
                "ans": ans_contents,
                "loss": loss,
                "feed_dict": feed_dict,
                "goal_outputs": goal_outputs
            }
            tr.set_description(f"GEN Loss: {loss:.03f}")
        sampler.remember(feed_dict, loss)

    return solution


def main(args):
    logging.getLogger("hyperopt").setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG)
    # Compile everything.
    subprocess.check_call(COMPILE_COMMAND + [args.generator, "-o", "gen"])
    subprocess.check_call(COMPILE_COMMAND + [args.solution, "-o", "sol"])
    # Figure out the params while running the generator in interactive mode.
    param_specs = {}
    # Read test files to figure out feed dicts.
    tests = parse_tests_file(args.tests)
    sampler = HyperoptSampler()

    for test_dict in tests:
        test_name = test_dict.pop('#')
        idx = 0
        goal_targets = []
        while f'G{idx}' in test_dict:
            goal_targets.append(float(test_dict.pop(f'G{idx}')))
            idx += 1

        logging.info(f"Generating test '{test_name}'...")
        logging.info(f"Goal targets: {goal_targets}")

        tick = time.perf_counter()
        solution = generate_test(
            sampler, test_dict, param_specs, goal_targets, args.n_iterations)
        tock = time.perf_counter()
        logging.info(
            f"Ran {args.n_iterations} iterations (time taken: {(tock - tick):.3f} s).")

        if solution is None:
            raise RuntimeError("Could not generate solution.")

        # print(f"Feed dict: {solution['feed_dict']}")
        logging.info(f"Targets: {goal_targets}")
        logging.info(f"Outputs: {solution['goal_outputs']}")
        logging.info(f"(loss: {solution['loss']})")
        logging.debug(solution['feed_dict'])

        os.makedirs(args.output_dir, exist_ok=True)
        format_map = {"name": test_name}
        in_filename = os.path.join(
            args.output_dir, args.in_pattern.format_map(format_map))
        ans_filename = os.path.join(
            args.output_dir, args.ans_pattern.format_map(format_map))
        with open(in_filename, 'w') as infile:
            infile.write(solution["in"])
            logging.info(f"Input file written to '{in_filename}'")
        with open(ans_filename, 'w') as ansfile:
            ansfile.write(solution["ans"])
            logging.info(f"Answer file written to '{ans_filename}'")

    logging.info("Cleaning up...")
    os.remove("./sol")
    os.remove("./gen")
    logging.info("Done!")


if __name__ == "__main__":
    main(parse_args())
