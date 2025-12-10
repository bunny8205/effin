# effin/node/__main__.py
import dotenv
dotenv.load_dotenv()

from effin.node.app import main
import asyncio, os

if __name__ == "__main__":
    asyncio.run(main(
        tps=float(os.getenv("TPS", "2.0")),
        workers=int(os.getenv("WORKERS", "2"))
    ))
