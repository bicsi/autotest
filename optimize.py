import subprocess
import argparse
import time
import random
import os
# import hyperopt as hp

COMPILE_COMMAND = ['g++', '-std=c++11']
TU_PARAM_REQ = 'TU_PARAM_REQ'


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
                        default=10,
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
    sexp = sexp.strip()

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


def figure_out_param_specs(generator_exec_path):
    param_specs = {}
    with subprocess.Popen(
            [generator_exec_path, '--interactive'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE) as process:
        while process.poll() is None:
            line = process.stdout.readline().decode('UTF-8')
            if not line:
                time.sleep(1)
            if line.startswith(TU_PARAM_REQ):
                _, param_name, param_spec = line.split(maxsplit=2)
                param_spec = parse_spec(param_spec)
                param_specs[param_name] = param_spec
                param_value = generate_feasible_value(param_spec)
                process.stdin.write(f"{param_value}\n".encode('UTF-8'))
                process.stdin.flush()
        return_code = process.wait()
        if return_code != 0:
            print(f'Generator retured exit code: {return_code}')
            exit(-1)
    return param_specs


def run_generator(generator_exec_path, feed_dict):
    args = [generator_exec_path]
    for name, value in feed_dict.items():
        args.append(f"-P{name}")
        args.append(str(value))
    return subprocess.check_output(args).decode('UTF-8')


def run_solution(solution_exec_path, in_contents):
    with subprocess.Popen(
            [solution_exec_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE) as process:
        stdout, stderr = process.communicate(
            input=in_contents.encode('UTF-8'), timeout=10)
        if process.returncode != 0:
            # an error happened!
            err_msg = "%s. Code: %s" % (stderr.strip(), process.returncode)
            raise RuntimeError(err_msg)
        obj_outputs = list(map(float, stderr.decode(
            'UTF-8').strip().splitlines()[-1].split()))
        return stdout.decode('UTF-8'), obj_outputs


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


def main(args):
    # Compile everything.
    subprocess.check_call(COMPILE_COMMAND + [args.generator, "-o", "gen"])
    subprocess.check_call(COMPILE_COMMAND + [args.solution, "-o", "sol"])
    # Figure out the params by running the generator in interactive mode.
    param_specs = figure_out_param_specs('./gen')
    # Read test files to figure out feed dicts.
    tests = parse_tests_file(args.tests)

    for test_dict in tests:
        test_name = test_dict.pop('#')
        obj_targets = list(map(float, [test_dict.pop('obj')]))
        solution = None

        print(f"Generating test '{test_name}'...")
        tick = time.perf_counter()
        for _ in range(args.n_iterations):
            feed_dict = test_dict.copy()
            for param in param_specs:
                if param in feed_dict:
                    continue
                feed_dict[param] = generate_feasible_value(param_specs[param])
            in_contents = run_generator('./gen', feed_dict)
            ans_contents, obj_outputs = run_solution('./sol', in_contents)
            assert len(obj_outputs) == len(obj_targets)
            loss = 0
            for i in range(len(obj_targets)):
                loss += (obj_targets[i] - obj_outputs[i]) ** 2
            if solution is None or solution['loss'] > loss:
                solution = {
                    "in": in_contents,
                    "ans": ans_contents,
                    "loss": loss,
                    "feed_dict": feed_dict,
                    "obj_outputs": obj_outputs
                }
        tock = time.perf_counter()
        print(
            f"Ran {args.n_iterations} iterations (time taken: {(tock - tick):.3f} s).")
        # print(f"Feed dict: {solution['feed_dict']}")
        print(f"Targets: {obj_targets}")
        print(f"Outputs: {solution['obj_outputs']}")
        print(f"(loss: {solution['loss']})")

        os.makedirs(args.output_dir, exist_ok=True)
        format_map = {"name": test_name}
        in_filename = os.path.join(
            args.output_dir, args.in_pattern.format_map(format_map))
        ans_filename = os.path.join(
            args.output_dir, args.ans_pattern.format_map(format_map))
        with open(in_filename, 'w') as infile:
            infile.write(solution["in"])
            print(f"Input file written to '{in_filename}'")
        with open(ans_filename, 'w') as ansfile:
            ansfile.write(solution["ans"])
            print(f"Answer file written to '{ans_filename}'")
        print('-' * 20)


if __name__ == "__main__":
    main(parse_args())
