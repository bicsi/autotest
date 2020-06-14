#pragma once

#include <algorithm>
#include <vector>

#include "params.hpp"

namespace testutils {

struct TreeGen {
  FloatParam a;
  FloatParam b;
  TreeGen() : a("tree/a", 0.0, 1e5), b("tree/b", 0.0, 1e5) {}

  std::vector<int> generate(int n, bool shuffle = true) {
    std::vector<int> order(n);
    std::iota(order.begin(), order.end(), 0);
    if (shuffle) std::shuffle(order.begin(), order.end(), rng);
    std::vector<double> samples(n - 1);
    // We use the Kumaraswamy distribution as a distribution very similar to the
    // Beta distribution but faster to sample.
    // https://en.wikipedia.org/wiki/Kumaraswamy_distribution
    auto dist = std::uniform_real_distribution<double>(0., 1.);
    for (int i = 0; i < n - 1; ++i) {
      double z = dist(rng);
      // 1 - (1 - x^a)^b = z
      double x = pow(1. - pow(1. - z, 1.0 / b.get()), 1.0 / a.get());
      x = std::min(x, 1 - 1e-9);
      x = std::max(x, 1e-9);
      samples[i] = x;
    }

    std::vector<int> ret(n, -1);
    for (int i = 1; i < n; ++i) {
      int j = (int)(samples[i - 1] * i);
      assert(j < i);
      ret[order[i]] = order[j];
    }
    return ret;
  }
};

}  // namespace testutils