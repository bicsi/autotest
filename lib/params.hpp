#pragma once

#include <algorithm>
#include <memory>
#include <vector>

#include "testutils.hpp"

namespace testutils {

const std::string TU_PARAM_REQ = "TU_PARAM_REQ";

std::string get_specs() {
  std::stringstream ss;
  ss << "(";
  bool first = true;
  for (auto p : SCOPE.param_specs) {
    if (!first) ss << " ";
    ss << "(" << p.first << " " << p.second << ")";
    first = false;
  }
  ss << ")";
  return ss.str();
}

template <typename TValue>
class Param {
 protected:
  std::string name;

  virtual TValue parse(std::string value) = 0;
  virtual std::string to_sexp() = 0;

  void _register() {
    if (SCOPE.param_specs.count(name)) {
      throw std::runtime_error("Multiple params registered for: '" + name +
                               "'");
    }
    SCOPE.param_specs[name] = to_sexp();
  }

 public:
  Param(std::string name) : name(name) {
    if (!SCOPE.params.count(name)) {
      DEBUG(std::cerr << "Param '" << name
                      << "' not found. Any call to param.get() will fail."
                      << std::endl);
    }
  }

  TValue get() {
    if (!SCOPE.params.count(name)) {
      if (SCOPE.interactive) {
        std::cout << TU_PARAM_REQ << " " << name << " " << to_sexp()
                  << std::endl;
        std::string value;
        std::cin >> value;
        SCOPE.params[name] = value;
      } else {
        auto specs = get_specs();
        std::ofstream fout(SCOPE.param_spec_output_filename);
        fout << specs << std::endl;
        throw std::runtime_error("Missing required param: '" + name +
                                 "' (specs dumped)");
      }
    }
    return parse(SCOPE.params[name]);
  }

  virtual ~Param() {}
};

class ChoiceParam : public Param<std::string> {
  std::vector<std::string> choices;

 public:
  ChoiceParam(std::string name, std::vector<std::string> choices)
      : Param<std::string>(name), choices(choices) {
    _register();
  }

  std::string parse(std::string value) {
    if (std::count(choices.begin(), choices.end(), value)) {
      return value;
    }
    throw std::runtime_error("Value '" + value + "' not amongst choices.");
  }

  std::string to_sexp() {
    std::stringstream ss;
    ss << "((type choice) (choices (";
    for (int i = 0; i < (int)choices.size(); ++i) {
      if (i > 0) ss << " ";
      ss << choices[i];
    }
    ss << ")))";
    return ss.str();
  }
};

class FloatParam : public Param<double> {
  double min, max;

 public:
  FloatParam(std::string name, double min = 0.0, double max = 1.0)
      : Param<double>(name), min(min), max(max) {
    _register();
  }

  double parse(std::string s_value) {
    double value = stod(s_value);
    if (value < min || value > max)
      throw std::runtime_error("Value '" + std::to_string(value) +
                               "' out of bounds.");
    return value;
  }

  std::string to_sexp() {
    std::stringstream ss;
    ss << "((type float) (min " << min << ") (max " << max << "))";
    return ss.str();
  }
};

class IntegerParam : public Param<long long> {
  long long min, max;

 public:
  IntegerParam(std::string name, long long min = 0, long long max = INT_MAX)
      : Param<long long>(name), min(min), max(max) {
    _register();
  }

  long long parse(std::string s_value) {
    long long value = stoll(s_value);
    if (value < min || value > max)
      throw std::runtime_error("Value '" + std::to_string(value) +
                               "' out of bounds.");
    return value;
  }

  std::string to_sexp() {
    std::stringstream ss;
    ss << "((type int) (min " << min << ") (max " << max << "))";
    return ss.str();
  }
};

}  // namespace testutils
