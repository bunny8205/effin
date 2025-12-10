# tests/test_search.py
import pytest, asyncio, numpy as np, os
from effin.node.search import CyborgWrapper

@pytest.mark.asyncio
async def test_create_and_upsert():
    cy = CyborgWrapper(os.getenv("CYBORGDB_ENDPOINT","http://localhost:8000"), os.getenv("CYBORGDB_API_KEY","dev"), os.getenv("INDEX_KEY",""))
    await cy.create_index("test_index_unit", 32)
    res = await cy.upsert("test_index_unit", "id1", np.random.rand(32), {"k":"v"})
    assert "status" in res or res is not None
    await cy.close()
