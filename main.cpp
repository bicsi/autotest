#include <bits/stdc++.h>

#include <cassert>

#include "generators.hpp"

using namespace testutils;

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

  SCOPE.params["tree/b"] = "0.001";
  for (int i = 0; i < 2; ++i) {
    auto par = tg.generate(n);
    std::vector<std::vector<int>> graph(n);
    int root = -1;
    for (int i = 0; i < n; ++i) {
      if (par[i] != -1) {
        graph[i].push_back(par[i]);
        graph[par[i]].push_back(i);
      } else
        root = i;
    }

    root = DFS(graph, root, -1, 0).second;
    int diam = DFS(graph, root, -1, 0).first;

    std::cout << get_specs() << std::endl;
    std::cout << diam << std::endl;
    SCOPE.params["tree/b"] = "1000.";
  }
  return 0;
}