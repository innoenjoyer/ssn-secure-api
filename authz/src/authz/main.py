import os

import httpx
import jwt
from fastapi import FastAPI, Request, Response

HYDRA_PUBLIC = os.getenv('HYDRA_PUBLIC', 'http://hydra:4444')
HYDRA_ADMIN = os.getenv('HYDRA_ADMIN', 'http://hydra:4445')
ALL_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

app = FastAPI()
jwks = jwt.PyJWKClient(f'{HYDRA_PUBLIC}/.well-known/jwks.json', cache_keys=True)


def bearer(request: Request) -> str | None:
    h = request.headers.get('authorization', '')
    return h[7:] if h.lower().startswith('bearer ') else None


def ok(client_id: str, scopes: str) -> Response:
    return Response(
        status_code=200,
        headers={
            'X-Client-Id': client_id or 'unknown',
            'X-Scopes': scopes or 'none',
        },
    )


@app.api_route('/verify/jwt', methods=ALL_METHODS)
def verify_jwt(request: Request) -> Response:
    token = bearer(request)
    if not token:
        return Response(status_code=401)
    try:
        key = jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=['RS256'], options={'verify_aud': False})
    except jwt.PyJWTError:
        return Response(status_code=401)
    return ok(claims.get('client_id', claims.get('sub', '')), ' '.join(claims.get('scp', [])))


@app.api_route('/verify/introspect', methods=ALL_METHODS)
async def verify_introspect(request: Request) -> Response:
    token = bearer(request)
    if not token:
        return Response(status_code=401)
    async with httpx.AsyncClient(timeout=3) as c:
        r = await c.post(f'{HYDRA_ADMIN}/admin/oauth2/introspect', data={'token': token})
    data = r.json() if r.status_code == 200 else {}
    if not data.get('active'):
        return Response(status_code=401)
    return ok(data.get('client_id', ''), data.get('scope', ''))
