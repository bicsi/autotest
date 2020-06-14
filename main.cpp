#include <bits/stdc++.h>

#include <cassert>

#include "lib/generators.hpp"

using namespace testutils;
using namespace std;

std::pair<int, int> DFS(std::vector<std::vector<int>>& graph, int node, int par,
                        int dep) {
  std::pair<int, int> best = {dep, node};
  for (auto vec : graph[node]) {
    if (vec == par) continue;
    best = max(best, DFS(graph, vec, node, dep + 1));
  }
  return best;
}

int main(int argc, char** argv) {
  init(argc, argv);
  TreeGen tg;

  int n = 1000;
  auto par = tg.generate(n);
  for (int i = 0; i < n; ++i) {
    if (par[i] != -1) {
      cout << i + 1 << " " << par[i] + 1 << '\n';
    }
  }
  return 0;
}