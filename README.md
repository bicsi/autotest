# Autotest

#### An goal-oriented automatic test generation framework for competitive programming problem-setting.

With a header-only implementation in pure C++ (no extra libraries!)

## What does that mean?

What this framework aims to be is a way to create test cases by focusing less on writing generators and by focusing more on what it is that you're trying to achieve for a given test case, while reusing expressive generic generators.

## How to install

```bash
pip install -r requirements.txt
```

## How to use

You can use the autotest framework by following some simple steps (that you would have had, anyways, on a problem-setting scenario)

1. Create a generator
2. Create a model solution
3. Create the specifications (parameters) for each test case
4. Run the `autotest.py` script

## Creating a generator

First you have to create a _parameterized generator source file_ which will generate your code.

**Make sure you add**

```c++
autotest::init(argc, argv);
```

**as the first line of the program!** This will initialize the autotest framework for generators.

To include (hyper)parameters in your source file, it's as simple as just declaring an `autotest::Param<T>` instance inside your code and calling its `.get()` method (take note though, that you cannot instantiate a `Param<T>` class, but you can use its specialized types found inside the `params.hpp` file).

For example, declaring a parameter `N` inside your code would be as simple as:

```c++
int N = autotest::IntegerParam("N", 1, 100000).get();
```

You can add multiple parameter types (integers, floating-point, choices). Please refer to the examples or read the code for more info.

Finally, code the rest of the generator as usual.

**Note: You can add various parameter names, but don't use `"G0"`, `"G1"`, ... for the names, as these should be reserved for goal names.**

## Creating a model solution

This step is rather straightforward: just code the solution as you would (_the framework doesn't help you from coding an incorrect solution as the model solution!_). The only thing that you have to do extra is to **write a line before exiting with some goal metrics computed**.

For example, let's say that you want to generate test cases for a problem on trees, and you have figured that a brute force solution is of complexity `O(N * D)`, where `D` is the diameter of the tree. As the diameter of the tree itself might be a metric good for optimization, in your solution you would end by writing:

```c++
std::cerr << diameter_of_tree << std::endl;
```

This allows the framework to the metric(s) that you want to optimize, by writing them **on the last line of `stderr`** (space-separated).

And, on the plus side, you can just sumbit the model solution on any OJ for testing without changing a single line of code!

## Creating the test specifications

This step might be easier to grasp by looking at exaples rather than having a clear documentation, as the specifics of the format might change over time.

In essence, the test specification file is like a table written inside a text file. The first row is the header and should contain the special column name `#`, as long as the names of the fixed parameters inside a given test case.

**These parameters should match the ones specified as the first argument when creating the `autotest::Param<T>` objects in the generator file!**

Then, each subsequent line should contain a test configuration, starting with a test identifier (column marked `#`) and the parameter values.

Finally, you should add extra columns for each of the **goal variables** that you output inside the model solution, and their target values for each test case.

For example, let's continue with our diameter example, and consider an example where I want to create a test case that is just over the limit for a solution that is `O(N * D)` for our toy problem. The spec file should look as follows:

```txt
#                        N         G0
tryhard-micro-optimizers 300000    1112
```

This will tell the framework to generate a test that has the goal as close as possible to `1112` using the generator, where parameter named `N` will be fed value `300000`.

**Note: Parameters that are missing from the test specifications are assumed to not have any constraints, and will be used to their best by the autotest optimizer in order to optimize the goal metrics.**

## Run the autotest script

This is as simple as running

```bash
python3 autotest.py -n NUMBER_OF_TRIALS
```

For help with running the script, please run

```bash
python3 autotest.py --help
```

Congratulations! You have generated your first test case suite using autotest!

## Under the hood

The `autotest` framework uses the `hyperopt` library that is an implementation of hyperparameter tuning using the "Tree of Parzen Estimators" algorithm.

More information can be found on their official documentation page: http://hyperopt.github.io/hyperopt/

## Found bugs?

This is still in very early development. Please make sure to post a GitHub issue if you found any bugs.
