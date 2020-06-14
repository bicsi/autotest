import subprocess
import argparse
import json
import time
import hyperopt as hp

COMPILE_COMMAND = ['g++', '-std=c++11']
TU_PARAM_REQ = 'TU_PARAM_REQ'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--generator", type=str,
                        help="Generator file (e.g. gen.cpp)")
    parser.add_argument('-n', '--n-iterations', type=int,
                        help='Number of iterations (calls to generator)')
    return parser.parse_args()


def generate_feasible_value(spec):
    if spec['type'] == 'FLOAT':
        value = 0.5 * (float(spec['min']) + float(spec['max']))
    elif spec['type'] == 'INTEGER':
        value = (int(spec['min']) + int(spec['max'])) // 2
    elif spec['type'] == 'CHOICE':
        value = spec['choices'][0]
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
                param_spec = json.loads(param_spec)
                param_specs[param_name] = param_spec
                param_value = generate_feasible_value(param_spec)
                process.stdin.write(f"{param_value}\n".encode('UTF-8'))
                process.stdin.flush()
        return_code = process.wait()
        if return_code != 0:
            print(f'Generator retured exit code: {return_code}')
            exit(-1)
    return param_specs


def generate(generator_exec_path, feed_dict):
    args = [generator_exec_path]
    for name, value in feed_dict.items():
        args.append(f"-P{name}")
        args.append(str(value))
    return subprocess.check_output(args).decode('UTF-8')


def main(args):
    subprocess.check_call(COMPILE_COMMAND + [args.generator, "-o", "gen"])
    # Figure out the params by running the generator in interactive mode.
    param_specs = figure_out_param_specs('./gen')

    feed_dict = {
        "n": 10,
        "tree/a": 10.0,
        "tree/b": 10.0,
    }
    print(param_specs)
    print(generate('./gen', feed_dict))


if __name__ == "__main__":
    main(parse_args())
