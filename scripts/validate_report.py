"""Validate report JSON against Microsoft's published PBIR schemas."""
from pathlib import Path
import sys,json,urllib.request,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.tools'))
sys.path.insert(0,str(ROOT/'.validation-tools'))
from jsonschema import Draft7Validator, RefResolver
CACHE=ROOT/'qa/schemas'; CACHE.mkdir(exist_ok=True)
def fetch(url):
    # Microsoft's embedded schema $id uses a dot, while the published URL uses a hyphen.
    url=url.replace('schema.embedded.json','schema-embedded.json')
    p=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    if not p.exists(): p.write_bytes(urllib.request.urlopen(url).read())
    return json.loads(p.read_text())
files=list((ROOT/'Energy Intelligence/Energy Intelligence.Report/definition').rglob('*.json'))
errors=[]; n=0
for p in files:
    d=json.loads(p.read_text(encoding='utf-8-sig'))
    if '$schema' not in d: continue
    schema=fetch(d['$schema'])
    validator=Draft7Validator(schema,resolver=RefResolver(d['$schema'],schema,handlers={'https':fetch}))
    for e in validator.iter_errors(d): errors.append(f'{p.relative_to(ROOT)}: {list(e.path)} {e.message}')
    n+=1
result={'validated_files':n,'errors':errors}
(ROOT/'qa/report-schema-validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2)); sys.exit(bool(errors))
