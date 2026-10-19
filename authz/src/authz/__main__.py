import os

import uvicorn


def main() -> None:
    uvicorn.run(
        'authz.main:app',
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', '8000')),
    )


if __name__ == '__main__':
    main()
