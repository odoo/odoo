const path = require("path");

const required = require(path.join(__dirname, "_package.json")).engines.node;
const have = process.versions.node.split(".").map(Number);
const ok = required.split("||").some((range) => {
    const [, operator, ...version] = range.trim().match(/^(\^|>=)(\d+)(?:\.(\d+))?(?:\.(\d+))?$/);
    const want = version.map((part) => Number(part || 0));
    const cmp = have[0] - want[0] || have[1] - want[1] || have[2] - want[2];
    return cmp >= 0 && (operator === ">=" || have[0] === want[0]);
});
if (!ok) {
    console.log(
        `The JS tooling needs Node.js ${required}, you have ${process.version}: the JS and CSS files are not linted.`
    );
    console.log("Upgrade Node.js (e.g. with nvm), then run addons/web/tooling/reload.sh");
    process.exit(1);
}
