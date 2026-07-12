import { ArrayMap } from "../data_structures";

export class MatcherCache {
    matcherInfos = new Map();
    getStatelessFlags(regExp) {
        return regExp.flags.replace(/[gy]/g, "");
    }
    getMatcherKey(key) {
        let matcherKey;
        if (typeof key === "function") {
            matcherKey = key;
        } else if (key instanceof RegExp) {
            const statelessFlags = this.getStatelessFlags(key);
            matcherKey = `re:${key.source}/${statelessFlags}`;
        } else if (typeof key === "string") {
            matcherKey = `str:${key}`;
        } else {
            throw new TypeError("Rule key must be a string, RegExp, or function.");
        }
        return matcherKey;
    }
    getMatcherInfo(key) {
        const matcherKey = this.getMatcherKey(key);
        if (!this.matcherInfos.has(matcherKey)) {
            let isName = false;
            let matcher;
            if (typeof key === "function") {
                matcher = key;
            } else if (key instanceof RegExp) {
                const statelessRegExp = new RegExp(key.source, this.getStatelessFlags(key));
                matcher = (name) => statelessRegExp.test(name);
            } else if (typeof key === "string") {
                matcher = (name) => name === key;
                isName = true;
            }
            if (matcher) {
                this.matcherInfos.set(matcherKey, {
                    matcherKey,
                    matcher,
                    isName,
                });
            }
        }
        return this.matcherInfos.get(matcherKey);
    }
}

const RULE_EFFECTS = ["allow", "block", "fix", "require"];

export class Rule {
    constructor({ key, effect, how, when, matcherCache, pluginId }) {
        const { isName, matcher, matcherKey } = matcherCache.getMatcherInfo(key);
        if (!RULE_EFFECTS.includes(effect)) {
            throw new TypeError(`Rule "effect" must be "allow", "block", "fix" or "require"`);
        }
        if (!isName && effect === "require") {
            throw new TypeError(`Rule "require" must specify a string "key"`);
        }
        if (typeof how !== "function" && effect === "fix") {
            throw new TypeError(`Rule "fix" must specify a function "how"`);
        }
        this.pluginId = pluginId;
        this.key = key;
        if (how) {
            this.how = (...args) => {
                this.howResult = how(...args);
                return this.howResult;
            };
        }
        this.matcherKey = matcherKey;
        this.matcher = matcher;
        this.effect = effect;
        this.conditions = this.addConditions(when);
    }
    addConditions(when) {
        const conditions = (Array.isArray(when) ? when : [when]).filter(
            (c) => typeof c === "function"
        );
        if (!conditions.length) {
            conditions.push(() => true);
        }
        return conditions;
    }
    /**
     * Combine every condition result with AND, ignoring conditions that return
     * undefined. If the combination is an empty array, return undefined
     * (same logic as plugins checkPredicates).
     */
    checkConditions(...args) {
        const results = this.conditions
            .map((condition) => condition(...args))
            .filter((result) => result !== undefined);
        return results.length ? results.every(Boolean) : undefined;
    }
}

export class Rules {
    // Rules (by name, string)
    allowingNameRules = new ArrayMap();
    blockingNameRules = new ArrayMap();
    fixingNameRules = new ArrayMap();
    requiringNameRules = new ArrayMap();
    // Rules (by matcherKey, function and RegExp)
    allowingMatcherKeyRules = new ArrayMap();
    blockingMatcherKeyRules = new ArrayMap();
    fixingMatcherKeyRules = new ArrayMap();
    // Matcher cache
    matcherCache = new MatcherCache();
    /**
     * @param {Object} [options]
     * @param {boolean} [defaultAllowed=false]
     *   Fallback decision when no rule matches.
     *   - false: unmatched keys are treated as blocked
     *   - true: unmatched keys are treated as allowed
     */
    constructor({ defaultAllowed = false } = {}) {
        this.defaultAllowed = defaultAllowed;
    }
    // External API
    forPlugin(pluginId) {
        return {
            allow: (key, options) => this.allow(key, { ...options, pluginId }),
            block: (key, options) => this.block(key, { ...options, pluginId }),
            fix: (key, options) => this.fix(key, { ...options, pluginId }),
            require: (key, options) => this.require(key, { ...options, pluginId }),
        };
    }
    allow(key, options = {}) {
        const { when, otherwise, pluginId } = options;
        const { matcherKey, isName } = this.matcherCache.getMatcherInfo(key);
        const rule = new Rule({
            key,
            effect: "allow",
            when,
            matcherCache: this.matcherCache,
            pluginId,
        });
        if (isName) {
            this.allowingNameRules.concat([rule], key);
        } else {
            this.allowingMatcherKeyRules.concat([rule], matcherKey);
        }
        if (when) {
            this.addOtherwise(rule, otherwise, options);
        }
    }
    block(key, options = {}) {
        const { when, otherwise, pluginId } = options;
        const { matcherKey, isName } = this.matcherCache.getMatcherInfo(key);
        const rule = new Rule({
            key,
            effect: "block",
            when,
            matcherCache: this.matcherCache,
            pluginId,
        });
        if (isName) {
            this.blockingNameRules.concat([rule], key);
        } else {
            this.blockingMatcherKeyRules.concat([rule], matcherKey);
        }
        if (when) {
            this.addOtherwise(rule, otherwise, options);
        }
    }
    fix(key, options = {}) {
        const { how, otherwise, when, pluginId } = options;
        const { matcherKey, isName } = this.matcherCache.getMatcherInfo(key);
        const rule = new Rule({
            key,
            effect: "fix",
            how,
            when,
            matcherCache: this.matcherCache,
            pluginId,
        });
        if (isName) {
            this.fixingNameRules.concat([rule], key);
        } else {
            this.fixingMatcherKeyRules.concat([rule], matcherKey);
        }
        if (when) {
            this.addOtherwise(rule, otherwise, options);
        }
    }
    require(name, options = {}) {
        const { when, otherwise, pluginId } = options;
        const rule = new Rule({
            key: name,
            effect: "require",
            when,
            matcherCache: this.matcherCache,
            pluginId,
        });
        this.requiringNameRules.concat([rule], name);
        if (when) {
            this.addOtherwise(rule, otherwise, options);
        }
    }
    processData(
        dataMap,
        {
            getRuleArgs = (...args) => args,
            onPass = () => {},
            onFail = () => {},
            onMiss = () => {},
        } = {}
    ) {
        const missing = new Map(
            [...this.requiringNameRules.keys()].map((name) => [name, undefined])
        );
        const _onFail = (name, value) => {
            if (missing.has(name)) {
                missing.set(name, value);
            }
            onFail(name, value);
        };
        const _onPass = (name, value, fix) => {
            if (this.requiringNameRules.has(name)) {
                missing.delete(name);
            }
            onPass(name, value, fix);
        };
        for (const [name, value] of dataMap) {
            let fixingRule;
            try {
                const fixingRules = this.getFixingRules(name);
                if (
                    fixingRules.length > 0 &&
                    (fixingRule = this.findFixingRule(fixingRules, ...getRuleArgs(name, value)))
                ) {
                    _onPass(name, value, fixingRule.howResult);
                    continue;
                }
                const blockingRules = this.getBlockingRules(name);
                if (
                    blockingRules.length > 0 &&
                    this.checkRules(blockingRules, ...getRuleArgs(name, value))
                ) {
                    _onFail(name, value);
                    continue;
                }
                const allowingRules = this.getAllowingRules(name);
                if (
                    allowingRules.length > 0 &&
                    this.checkRules(allowingRules, ...getRuleArgs(name, value))
                ) {
                    _onPass(name, value);
                    continue;
                }
                if (this.defaultAllowed) {
                    _onPass(name, value);
                } else {
                    _onFail(name, value);
                }
            } finally {
                if (fixingRule) {
                    fixingRule.howResult = undefined;
                }
            }
        }
        for (const [name, value] of missing) {
            const requiringRules = this.getRequiringRules(name);
            if (
                requiringRules.length > 0 &&
                this.checkRules(requiringRules, ...getRuleArgs(name, value))
            ) {
                onMiss(name, value);
            }
        }
    }
    // Internal functions
    addRule(key, options = {}) {
        const { effect } = options;
        if (effect === "allow") {
            this.allow(key, options);
        } else if (effect === "block") {
            this.block(key, options);
        } else if (effect === "fix") {
            this.fix(key, options);
        } else if (effect === "require") {
            this.require(key, options);
        }
    }
    addOtherwise(rule, otherwise, options = {}) {
        if (!otherwise || otherwise === rule.effect) {
            return;
        }
        let when = (...args) => {
            const result = rule.checkConditions(...args);
            return result === undefined ? undefined : !result;
        };
        if (rule.effect === "fix") {
            // For a fix, otherwise applies when the fix "when" returns true, but
            // there was no applicable fix (howResult is undefined)
            when = (...args) => rule.howResult === undefined && rule.checkConditions(...args);
        }
        options = { ...options, when, effect: otherwise };
        delete options.otherwise;
        this.addRule(rule.key, options);
    }
    /**
     * Combine every rule conditions check results with OR, ignoring checks
     * that return undefined. If the combination is an empty array, return
     * undefined.
     */
    checkRules(rules, ...args) {
        const results = rules
            .map((rule) => rule.checkConditions(...args))
            .filter((ruleResult) => ruleResult !== undefined);
        return results.length ? results.some(Boolean) : undefined;
    }
    findFixingRule(fixingRules, ...args) {
        return fixingRules.find(
            (fixingRule) =>
                fixingRule.checkConditions(...args) && fixingRule.how(...args) !== undefined
        );
    }
    getAllowingRules(name) {
        return this.getRules(name, this.allowingNameRules, this.allowingMatcherKeyRules);
    }
    getBlockingRules(name) {
        return this.getRules(name, this.blockingNameRules, this.blockingMatcherKeyRules);
    }
    getFixingRules(name) {
        return this.getRules(name, this.fixingNameRules, this.fixingMatcherKeyRules);
    }
    getRequiringRules(name) {
        return this.getRules(name, this.requiringNameRules);
    }
    getRules(name, nameRules, matcherKeyRules) {
        const matchingRules = [];
        if (nameRules.has(name)) {
            matchingRules.push(...nameRules.get(name));
        }
        if (!matcherKeyRules) {
            return matchingRules;
        }
        for (const [matcherKey, rules] of matcherKeyRules) {
            const { matcher } = this.matcherCache.matcherInfos.get(matcherKey);
            if (matcher(name)) {
                matchingRules.push(...rules);
            }
        }
        return matchingRules;
    }
    /**
     * Useful for debugging, map rule instances to their check result
     * (verification that a specific rule would apply or not) for a specific
     * processing case.
     */
    getRulesResults(name, value, getRuleArgs) {
        const mapToResult = (rule) => [rule, rule.checkConditions(...getRuleArgs(name, value))];
        return {
            allow: this.getAllowingRules(name).map(mapToResult),
            block: this.getBlockingRules(name).map(mapToResult),
            fix: this.getFixingRules(name).map(mapToResult),
            require: this.getRequiringRules(name).map(mapToResult),
        };
    }
}
