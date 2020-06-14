#pragma once

#include <algorithm>
#include <vector>

#include "params.hpp"

namespace testutils {

// We use the Kumaraswamy distribution as a distribution very similar to the
// Beta distribution but faster to sample.
// https://en.wikipedia.org/wiki/Kumaraswamy_distribution
double kumaraswamy_random(double a, double b) {
  auto dist = std::uniform_real_distribution<double>(0., 1.);
  double z = dist(rng);
  // 1 - (1 - x^a)^b = z
  double x = pow(1. - pow(1. - z, 1.0 / b), 1.0 / a);
  x = std::min(x, 1 - 1e-9);
  x = std::max(x, 1e-9);
  return x;
}

class TreeGen {
  FloatParam a, b;

 public:
  TreeGen() : a("tree/a", 0.0, 1e5), b("tree/b", 0.0, 1e5) {}

  std::vector<int> generate(int n, bool shuffle = true) {
    std::vector<int> order(n);
    std::iota(order.begin(), order.end(), 0);
    if (shuffle) std::shuffle(order.begin(), order.end(), rng);
    std::vector<double> samples(n - 1);
    for (int i = 0; i < n - 1; ++i) {
      samples[i] = kumaraswamy_random(a.get(), b.get());
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

class PartitionGen {
  FloatParam a, b;

 public:
  PartitionGen() : a("partition/a", 0.0, 1e5), b("partition/b", 0.0, 1e5) {}

  std::vector<long long> generate(int n, long long s) {
    std::vector<double> samples(n);
    double sum = 0;
    for (int i = 0; i < n; ++i) {
      samples[i] = kumaraswamy_random(a.get(), b.get());
      sum += samples[i];
    }
    std::vector<long long> values(n);
    long long check_sum = 0;
    for (int i = 0; i < n; ++i) {
      values[i] = round(samples[i] * s / sum);
      check_sum += values[i];
    }
    while (check_sum != s) {
      int idx = rng() % values.size();
      values[idx] += (check_sum < s ? +1 : -1);
      check_sum += (check_sum < s ? +1 : -1);
    }
    return values;
  }
};

}  // namespace testutils