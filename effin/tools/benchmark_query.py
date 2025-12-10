# tools/benchmark_query.py
import time, numpy as np, os, asyncio
from effin.node.search import CyborgWrapper

async def run():
    cy = CyborgWrapper(os.getenv("CYBORGDB_ENDPOINT","http://localhost:8000"), os.getenv("CYBORGDB_API_KEY","dev"), os.getenv("INDEX_KEY",""))
    # generate 200 random vectors
    vectors = [np.random.rand(384).astype(float) for _ in range(200)]
    lat = []
    for v in vectors:
        t0 = time.time()
        await cy.query(os.getenv("INDEX_NAME","fraud_demo"), v, top_k=5)
        lat.append(time.time()-t0)
    lat_sorted = sorted(lat)
    print("p50", lat_sorted[int(0.5*len(lat))])
    print("p95", lat_sorted[int(0.95*len(lat))])
    print("p99", lat_sorted[min(int(0.99*len(lat)), len(lat)-1)])
    await cy.close()

if __name__=="__main__":
    asyncio.run(run())
