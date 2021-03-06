#pragma once

#include <iostream>
#include <map>

#ifdef TU_DEBUG
#define DEBUG(x) (x)
#else
#define DEBUG(x)
#endif

namespace autotest {

struct Scope {
  std::map<std::string, std::string> params;
  std::map<std::string, std::string> param_specs;
  std::string param_spec_output_filename = "/tmp/params.sexp";
  uint64_t seed;
  bool interactive;
} SCOPE;

std::mt19937_64 rng;

uint64_t _compute_seed(int argc, char** argv) {
  const uint64_t multiplier = 0x5DEECE66DLL;
  const uint64_t addend = 0xBLL;
  const uint64_t mask = (1LL << 48) - 1;

  uint64_t seed = 3905348978240129619LL;
  for (int i = 1; i < argc; i++) {
    std::size_t le = std::strlen(argv[i]);
    for (std::size_t j = 0; j < le; j++)
      seed = seed * multiplier + (uint16_t)(argv[i][j]) + addend;
    seed += multiplier / addend;
  }

  seed = seed & mask;
  return seed;
}

void init(int argc, char** argv) {
  auto seed = _compute_seed(argc, argv);
  rng = std::mt19937_64(seed);
  SCOPE.seed = seed;
  DEBUG(std::cerr << "Seed: " << seed << std::endl);

  for (int i = 1; i < argc; ++i) {
    char* arg = argv[i];
    // strlen(arg) >= 2 is implied by short-circuit here.
    if (arg[0] == '-' && arg[1] == 'P') {
      assert(i + 1 < argc);
      std::string param_name = arg + 2;
      std::string param_value = argv[++i];
      SCOPE.params[param_name] = param_value;
      DEBUG(std::cerr << "CLI param: " << param_name << " = " << param_value
                      << std::endl);
    } else if (strcmp(arg, "-po") == 0) {
      assert(i + 1 < argc);
      SCOPE.param_spec_output_filename = argv[++i];
      DEBUG(std::cerr << "params output override to: "
                      << SCOPE.param_spec_output_filename << std::endl);
    } else if (strcmp(arg, "--interactive") == 0) {
      SCOPE.interactive = true;
    } else {
      throw std::runtime_error(std::string() + "Unrecognized option: '" +
                               argv[i] + "'");
    }
  }
}

}  // namespace autotest
