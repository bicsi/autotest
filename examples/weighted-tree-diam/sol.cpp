#include <bits/stdc++.h>

using namespace std;

vector<int> parent, values;
vector<vector<int>> graph;

pair<int, int> DFS(int node, int par, int dep) {
  pair<int, int> ret = {dep, node};
  parent[node] = par;
  for (auto vec : graph[node]) {
    if (vec == par) continue;
    ret = max(ret, DFS(vec, node, dep + 1));
  }
  return ret;
}

int main() {
  int n;
  cin >> n;
  values.resize(n);
  parent.resize(n);
  graph.resize(n);
  for (int i = 0; i < n; ++i) cin >> values[i];
  for (int i = 1; i < n; ++i) {
    int a, b;
    cin >> a >> b;
    --a;
    --b;
    graph[a].push_back(b);
    graph[b].push_back(a);
  }
  int v = DFS(DFS(0, -1, 0).second, -1, 0).second;

  long long ans = 0;
  for (int node = v; node != -1; node = parent[node]) {
    ans += values[node];
  }
  cout << ans << endl;
  cerr << ans << endl;
  return 0;
}
