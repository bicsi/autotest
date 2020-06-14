#pragma once

#include <algorithm>
#include <memory>
#include <vector>

#include "testutils.hpp"

namespace testutils {

template <typename TValue>
class ParamSpec {
 public:
  virtual TValue convert(std::string value) = 0;
  virtual std::string str() = 0;
  virtual ParamSpec<TValue>* clone() = 0;
  virtual ~ParamSpec<TValue>() {}
};

class IntegerParamSpec : public ParamSpec<long long> {
  long long min, max;

 public:
  IntegerParamSpec(long long min = 0, long long max = INT_MAX)
      : min(min), max(max) {}

  long long convert(std::string s_value) {
    long long value = stoll(s_value);
    if (value < min)
      throw std::runtime_error("Value '" + std::to_string(value) +
                               "' too small.");
    if (value > max)
      throw std::runtime_error("Value '" + std::to_string(value) +
                               "' too large.");
    return value;
  }

  std::string str() {
    std::string ret;
    ret += "{";
    ret += "\"type\": \"INTEGER\"";
    ret += ", ";
    ret += "\"min\": " + std::to_string(min);
    ret += ", ";
    ret += "\"max\": " + std::to_string(max);
    ret += "}";
    return ret;
  }

  ParamSpec<long long>* clone() { return new IntegerParamSpec(*this); }
};

class FloatParamSpec : public ParamSpec<double> {
  double min, max;

 public:
  FloatParamSpec(double min = 0.0, double max = 1.0) : min(min), max(max) {}

  double convert(std::string s_value) {
    double value = stod(s_value);
    if (value < min)
      throw std::runtime_error("Value '" + std::to_string(value) +
                               "' too small.");
    if (value > max)
      throw std::runtime_error("Value '" + std::to_string(value) +
                               "' too large.");
    return value;
  }

  std::string str() {
    std::string ret;
    ret += "{";
    ret += "\"type\": \"FLOAT\"";
    ret += ", ";
    ret += "\"min\": " + std::to_string(min);
    ret += ", ";
    ret += "\"max\": " + std::to_string(max);
    ret += "}";
    return ret;
  }

  ParamSpec<double>* clone() { return new FloatParamSpec(*this); }
};

class ChoiceParamSpec : public ParamSpec<std::string> {
  std::vector<std::string> choices;

 public:
  ChoiceParamSpec(std::vector<std::string> choices) : choices(choices) {}

  std::string convert(std::string value) {
    if (std::count(choices.begin(), choices.end(), value)) {
      return value;
    }
    throw std::runtime_error("Value '" + value + "' not amongst choices.");
  }

  std::string str() {
    std::string ret;
    ret += "{";
    ret += "\"type\": \"CHOICE\"";
    ret += ", ";
    ret += "\"choices\": [";
    for (int i = 0; i < (int)choices.size(); ++i) {
      if (i > 0) ret += ", ";
      ret += "\"" + choices[i] + "\"";
    }
    ret += "]";
    ret += "}";
    return ret;
  }
  ParamSpec<std::string>* clone() { return new ChoiceParamSpec(*this); }
};

std::string get_specs() {
  std::string ans = "{";
  for (auto p : SCOPE.param_specs) {
    if (ans.size() != 1) ans += ", ";
    ans += "\"" + p.first + "\": " + p.second;
  }
  ans += "}";
  return ans;
}

template <typename TValue>
class Param {
  std::string name;
  std::unique_ptr<ParamSpec<TValue>> spec;

 public:
  Param(std::string name, ParamSpec<TValue>&& spec)
      : name(name), spec(spec.clone()) {
    if (!SCOPE.params.count(name)) {
      DEBUG(std::cerr << "Param '" << name
                      << "' not found. Any call to param.get() will fail."
                      << std::endl);
    }

    if (SCOPE.param_specs.count(name)) {
      throw std::runtime_error("Multiple params instantiated for: '" + name +
                               "'");
    }
    SCOPE.param_specs[name] = spec.str();
  }
  TValue get() {
    if (!SCOPE.params.count(name)) {
      auto specs = get_specs();
      std::ofstream fout(SCOPE.param_spec_output_filename);
      fout << specs << std::endl;
      throw std::runtime_error("Missing required param: '" + name +
                               "' (specs dumped)");
    }
    return spec->convert(SCOPE.params[name]);
  }
};

}  // namespace testutils
