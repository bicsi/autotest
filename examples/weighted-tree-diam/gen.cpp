#include <bits/stdc++.h>

#include "../../lib/generators.hpp"

using namespace autotest;
using namespace std;

int main(int argc, char** argv) {
  init(argc, argv);

  int n = IntegerParam("n", 1, 100000).get();
  int s = IntegerParam("s", 1, 1e9).get();

  auto par = TreeGen().generate(n);
  auto values = PartitionGen().generate(n, s);

  cout << n << '\n';
  for (int i = 0; i < n; ++i) {
    cout << values[i] << " ";
  }
  cout << '\n';
  for (int i = 0; i < n; ++i) {
    if (par[i] != -1) {
      cout << i + 1 << " " << par[i] + 1 << '\n';
    }
  }

  return 0;
}