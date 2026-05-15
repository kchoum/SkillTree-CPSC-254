# Advanced submission: Graph with Dijkstra's shortest path
# Issues: no negative weight check, uses float('inf') inconsistently,
# visited set missing causing potential revisits in dense graphs,
# no path reconstruction, heapq used correctly but priority queue
# entries not invalidated on relaxation (stale entries remain)

import heapq
from collections import defaultdict

class Graph:
    def __init__(self):
        self.adj = defaultdict(list)

    def add_edge(self, u, v, weight):
        self.adj[u].append((v, weight))
        self.adj[v].append((u, weight))

    def dijkstra(self, start):
        dist = defaultdict(lambda: float('inf'))
        dist[start] = 0
        pq = [(0, start)]

        while pq:
            d, u = heapq.heappop(pq)

            # Missing: if d > dist[u]: continue
            # This causes stale heap entries to be processed

            for v, w in self.adj[u]:
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    heapq.heappush(pq, (dist[v], v))

        return dict(dist)

    def bfs(self, start):
        from collections import deque
        visited = set()
        queue = deque([start])
        visited.add(start)
        order = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor, _ in self.adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return order

g = Graph()
edges = [(0,1,4),(0,2,1),(2,1,2),(1,3,1),(2,3,5)]
for u, v, w in edges:
    g.add_edge(u, v, w)

print(g.dijkstra(0))
print(g.bfs(0))
