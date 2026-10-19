# Securing API with OAuth2, Rate Limiting and WAF

- Target API service (FastAPI)
- Traefik (Coraza WAF, `rateLimit`, `forwardAuth`)
- authz + Ory Hydra.

## Run

```bash
docker compose up -d
```

## Client credentials & token

Get Hydra `client_id` & `client_secret`:

```bash
creds=$(docker compose logs hydra-init --no-log-prefix | tail -1)
export CID=$(jq -r .client_id <<<"$creds")
export CSECRET=$(jq -r .client_secret <<<"$creds")
```

Generate token:
```bash
TOKEN=$(curl -s -u "$CID:$CSECRET" -d grant_type=client_credentials -d scope=read \
  http://localhost:8080/oauth2/token | jq -r .access_token)
```

## Experiments

### SQLi

403 with WAF. Otherwise `flag{...}` leaks:

```bash
curl -G -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "q=' UNION SELECT id, name FROM items --" \
  http://localhost:8080/jwt/api/search
```

Baseline: Drop `SecRuleEngine` directive from the `waf` middleware in `traefik/dynamic.yml`.

### Brute force

Expect 429 once the limit is hit:

```bash
for i in $(seq 1 20); do
  curl -s -o /dev/null -w "%{http_code}\n" -d "username=admin&password=guess$i" http://localhost:8080/login
done
```

### Revoked token reuse

`/jwt` accepts until `exp`, `/introspect` rejects immediately:

```bash
curl -u "$CID:$CSECRET" -d "token=$TOKEN" http://localhost:8080/oauth2/revoke
curl -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" http://localhost:8080/jwt/api/items
curl -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" http://localhost:8080/introspect/api/items
```

The first call returns 200, the second returns 401.

- `/jwt` - naive/stateless: the token is checked locally against Hydra's JWKS
  (signature + `exp`). Fast and works even if Hydra is down, but it cannot see
  revocation, so a revoked token stays valid until it expires.
- `/introspect` - stateful: the gateway calls Hydra's introspection endpoint on
  every request. Revocation (and opaque tokens) take effect immediately, at the
  cost of a round-trip to Hydra per call.
