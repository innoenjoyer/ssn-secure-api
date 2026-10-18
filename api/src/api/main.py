import sqlite3
from collections.abc import Callable

from fastapi import Depends, FastAPI, Form, Header, HTTPException

app = FastAPI()
db = sqlite3.connect(':memory:', check_same_thread=False)
db.executescript("""
CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, secret INTEGER);
INSERT INTO items (name, secret) VALUES
  ('apple', 0), ('banana', 0), ('flag{waf_bypassed}', 1);
""")


def require_scope(scope: str) -> Callable[[str], None]:
    def check(x_scopes: str = Header(default='')) -> None:
        if scope not in x_scopes.split():
            raise HTTPException(403, f'missing scope: {scope}')

    return check


@app.get('/api/items', dependencies=[Depends(require_scope('read'))])
def list_items() -> list[dict[str, object]]:
    rows = db.execute('SELECT id, name FROM items WHERE secret = 0').fetchall()
    return [{'id': r[0], 'name': r[1]} for r in rows]


@app.get('/api/search', dependencies=[Depends(require_scope('read'))])
def search(q: str) -> list[dict[str, object]]:
    sql = f"SELECT id, name FROM items WHERE secret = 0 AND name LIKE '%{q}%'"
    rows = db.execute(sql).fetchall()
    return [{'id': r[0], 'name': r[1]} for r in rows]


@app.post('/login')
def login(username: str = Form(), password: str = Form()) -> dict[str, bool]:
    if username == 'admin' and password == 'secretpass':
        return {'ok': True}
    raise HTTPException(401, 'bad credentials')
