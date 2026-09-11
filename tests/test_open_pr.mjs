// Execute the actual inline workflow script against a fake API, not a copy.
import assert from 'node:assert/strict';
import fs from 'node:fs';
const text = fs.readFileSync(new URL('../.github/workflows/reusable-open-pr.yml', import.meta.url), 'utf8');
const marker = '          script: |\n';
assert.equal(text.split(marker).length, 2);
const source = text.split(marker)[1].split('\n').filter(Boolean).map(line => {
  assert.ok(line.startsWith('            '));
  return line.slice(12);
}).join('\n');
const AsyncFunction = Object.getPrototypeOf(async function() {}).constructor;
const run = new AsyncFunction('github', 'context', 'core', 'process', source);
let tests = 0;
async function check({head='agents/test/task', base='main', kind='agent', existing=[], ahead=1, error=false, writes=0}={}) {
  const created = [];
  let compared = false;
  const github = {
    paginate: async (_fn, args) => {
      assert.equal(args.head, `rybskiworks:${head}`);
      assert.equal(args.base, base);
      assert.equal(args.state, 'all');
      return existing;
    },
    rest: {
      pulls: {list() {}, create: async data => {created.push(data); return {data:{number:1}};}},
      repos: {compareCommitsWithBasehead: async args => {
        compared = true; assert.equal(args.basehead, `${base}...${head}`);
        return {data:{ahead_by:ahead}};
      }},
    },
  };
  const execute = () => run(github, {repo:{owner:'rybskiworks',repo:'example'}}, {info() {}},
    {env:{HEAD_BRANCH:head, BASE_BRANCH:base, PR_KIND:kind}});
  if (error) await assert.rejects(execute); else await execute();
  assert.equal(created.length, writes);
  if (writes) {assert.equal(created[0].draft, true); assert.equal(created[0].base, base); assert.ok(compared);}
  tests++;
}
await check({writes:1});
await check({ahead:0});
await check({existing:[{state:'open',merged_at:null}]});
await check({existing:[{state:'closed',merged_at:null}]});
await check({existing:[{state:'closed',merged_at:'2026-01-01'}]});
await check({head:'upstream/vendor/main',kind:'upstream',existing:[{state:'closed',merged_at:'2026-01-01'}],writes:1});
await check({base:'migration/tool-model',writes:1});
for (const head of ['main','agents/../main','agents/a;echo','agents/a\nb','agents//a','agents/a.lock']) {
  await check({head,error:true});
}
await check({head:'agents/test/task',base:'agents/test/task',error:true});
await check({kind:'unknown',error:true});
console.log(`${tests} metadata-only PR scenarios passed; no live API requests made.`);
