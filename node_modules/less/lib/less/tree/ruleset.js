var Node = require("./node"),
    Rule = require("./rule"),
    Selector = require("./selector"),
    Element = require("./element"),
    contexts = require("../contexts"),
    defaultFunc = require("../functions/default"),
    getDebugInfo = require("./debug-info");

var Ruleset = function (selectors, rules, strictImports) {
    this.selectors = selectors;
    this.rules = rules;
    this._lookups = {};
    this.strictImports = strictImports;
};
Ruleset.prototype = new Node();
Ruleset.prototype.type = "Ruleset";
Ruleset.prototype.isRuleset = true;
Ruleset.prototype.isRulesetLike = true;
Ruleset.prototype.accept = function (visitor) {
    if (this.paths) {
        visitor.visitArray(this.paths, true);
    } else if (this.selectors) {
        this.selectors = visitor.visitArray(this.selectors);
    }
    if (this.rules && this.rules.length) {
        this.rules = visitor.visitArray(this.rules);
    }
};
Ruleset.prototype.eval = function (context) {
    var thisSelectors = this.selectors, selectors,
        selCnt, selector, i, hasOnePassingSelector = false;

    if (thisSelectors && (selCnt = thisSelectors.length)) {
        selectors = [];
        defaultFunc.error({
            type: "Syntax",
            message: "it is currently only allowed in parametric mixin guards,"
        });
        for (i = 0; i < selCnt; i++) {
            selector = thisSelectors[i].eval(context);
            selectors.push(selector);
            if (selector.evaldCondition) {
                hasOnePassingSelector = true;
            }
        }
        defaultFunc.reset();
    } else {
        hasOnePassingSelector = true;
    }

    var rules = this.rules ? this.rules.slice(0) : null,
        ruleset = new Ruleset(selectors, rules, this.strictImports),
        rule, subRule;

    ruleset.originalRuleset = this;
    ruleset.root = this.root;
    ruleset.firstRoot = this.firstRoot;
    ruleset.allowImports = this.allowImports;

    if(this.debugInfo) {
        ruleset.debugInfo = this.debugInfo;
    }

    if (!hasOnePassingSelector) {
        rules.length = 0;
    }

    // push the current ruleset to the frames stack
    var ctxFrames = context.frames;
    ctxFrames.unshift(ruleset);

    // currrent selectors
    var ctxSelectors = context.selectors;
    if (!ctxSelectors) {
        context.selectors = ctxSelectors = [];
    }
    ctxSelectors.unshift(this.selectors);

    // Evaluate imports
    if (ruleset.root || ruleset.allowImports || !ruleset.strictImports) {
        ruleset.evalImports(context);
    }

    // Store the frames around mixin definitions,
    // so they can be evaluated like closures when the time comes.
    var rsRules = ruleset.rules, rsRuleCnt = rsRules ? rsRules.length : 0;
    for (i = 0; i < rsRuleCnt; i++) {
        if (rsRules[i].evalFirst) {
            rsRules[i] = rsRules[i].eval(context);
        }
    }

    var mediaBlockCount = (context.mediaBlocks && context.mediaBlocks.length) || 0;

    // Evaluate mixin calls.
    for (i = 0; i < rsRuleCnt; i++) {
        if (rsRules[i].type === "MixinCall") {
            /*jshint loopfunc:true */
            rules = rsRules[i].eval(context).filter(function(r) {
                if ((r instanceof Rule) && r.variable) {
                    // do not pollute the scope if the variable is
                    // already there. consider returning false here
                    // but we need a way to "return" variable from mixins
                    return !(ruleset.variable(r.name));
                }
                return true;
            });
            rsRules.splice.apply(rsRules, [i, 1].concat(rules));
            rsRuleCnt += rules.length - 1;
            i += rules.length-1;
            ruleset.resetCache();
        } else if (rsRules[i].type === "RulesetCall") {
            /*jshint loopfunc:true */
            rules = rsRules[i].eval(context).rules.filter(function(r) {
                if ((r instanceof Rule) && r.variable) {
                    // do not pollute the scope at all
                    return false;
                }
                return true;
            });
            rsRules.splice.apply(rsRules, [i, 1].concat(rules));
            rsRuleCnt += rules.length - 1;
            i += rules.length-1;
            ruleset.resetCache();
        }
    }

    // Evaluate everything else
    for (i = 0; i < rsRules.length; i++) {
        rule = rsRules[i];
        if (!rule.evalFirst) {
            rsRules[i] = rule = rule.eval ? rule.eval(context) : rule;
        }
    }

    // Evaluate everything else
    for (i = 0; i < rsRules.length; i++) {
        rule = rsRules[i];
        // for rulesets, check if it is a css guard and can be removed
        if (rule instanceof Ruleset && rule.selectors && rule.selectors.length === 1) {
            // check if it can be folded in (e.g. & where)
            if (rule.selectors[0].isJustParentSelector()) {
                rsRules.splice(i--, 1);

                for(var j = 0; j < rule.rules.length; j++) {
                    subRule = rule.rules[j];
                    if (!(subRule instanceof Rule) || !subRule.variable) {
                        rsRules.splice(++i, 0, subRule);
                    }
                }
            }
        }
    }

    // Pop the stack
    ctxFrames.shift();
    ctxSelectors.shift();

    if (context.mediaBlocks) {
        for (i = mediaBlockCount; i < context.mediaBlocks.length; i++) {
            context.mediaBlocks[i].bubbleSelectors(selectors);
        }
    }

    return ruleset;
};
Ruleset.prototype.evalImports = function(context) {
    var rules = this.rules, i, importRules;
    if (!rules) { return; }

    for (i = 0; i < rules.length; i++) {
        if (rules[i].type === "Import") {
            importRules = rules[i].eval(context);
            if (importRules && importRules.length) {
                rules.splice.apply(rules, [i, 1].concat(importRules));
                i+= importRules.length-1;
            } else {
                rules.splice(i, 1, importRules);
            }
            this.resetCache();
        }
    }
};
Ruleset.prototype.makeImportant = function() {
    return new Ruleset(this.selectors, this.rules.map(function (r) {
                if (r.makeImportant) {
                    return r.makeImportant();
                } else {
                    return r;
                }
            }), this.strictImports);
};
Ruleset.prototype.matchArgs = function (args) {
    return !args || args.length === 0;
};
// lets you call a css selector with a guard
Ruleset.prototype.matchCondition = function (args, context) {
    var lastSelector = this.selectors[this.selectors.length-1];
    if (!lastSelector.evaldCondition) {
        return false;
    }
    if (lastSelector.condition &&
        !lastSelector.condition.eval(
            new contexts.Eval(context,
                context.frames))) {
        return false;
    }
    return true;
};
Ruleset.prototype.resetCache = function () {
    this._rulesets = null;
    this._variables = null;
    this._lookups = {};
};
Ruleset.prototype.variables = function () {
    if (!this._variables) {
        this._variables = !this.rules ? {} : this.rules.reduce(function (hash, r) {
            if (r instanceof Rule && r.variable === true) {
                hash[r.name] = r;
            }
            // when evaluating variables in an import statement, imports have not been eval'd
            // so we need to go inside import statements.
	        // guard against root being a string (in the case of inlined less)
            if (r.type === "Import" && r.root && r.root.variables) {
                var vars = r.root.variables();
                for(var name in vars) {
                    if (vars.hasOwnProperty(name)) {
                        hash[name] = vars[name];
                    }
                }
            }
            return hash;
        }, {});
    }
    return this._variables;
};
Ruleset.prototype.variable = function (name) {
    return this.variables()[name];
};
Ruleset.prototype.rulesets = function () {
    if (!this.rules) { return null; }

    var filtRules = [], rules = this.rules, cnt = rules.length,
        i, rule;

    for (i = 0; i < cnt; i++) {
        rule = rules[i];
        if (rule.isRuleset) {
            filtRules.push(rule);
        }
    }

    return filtRules;
};
Ruleset.prototype.prependRule = function (rule) {
    var rules = this.rules;
    if (rules) { rules.unshift(rule); } else { this.rules = [ rule ]; }
};
Ruleset.prototype.find = function (selector, self, filter) {
    self = self || this;
    var rules = [], match, foundMixins,
        key = selector.toCSS();

    if (key in this._lookups) { return this._lookups[key]; }

    this.rulesets().forEach(function (rule) {
        if (rule !== self) {
            for (var j = 0; j < rule.selectors.length; j++) {
                match = selector.match(rule.selectors[j]);
                if (match) {
                    if (selector.elements.length > match) {
                      if (!filter || filter(rule)) {
                        foundMixins = rule.find(new Selector(selector.elements.slice(match)), self, filter);
                        for (var i = 0; i < foundMixins.length; ++i) {
                          foundMixins[i].path.push(rule);
                        }
                        Array.prototype.push.apply(rules, foundMixins);
                      }
                    } else {
                        rules.push({ rule: rule, path: []});
                    }
                    break;
                }
            }
        }
    });
    this._lookups[key] = rules;
    return rules;
};
Ruleset.prototype.genCSS = function (context, output) {
    var i, j,
        charsetRuleNodes = [],
        ruleNodes = [],
        rulesetNodes = [],
        rulesetNodeCnt,
        debugInfo,     // Line number debugging
        rule,
        path;

    context.tabLevel = (context.tabLevel || 0);

    if (!this.root) {
        context.tabLevel++;
    }

    var tabRuleStr = context.compress ? '' : Array(context.tabLevel + 1).join("  "),
        tabSetStr = context.compress ? '' : Array(context.tabLevel).join("  "),
        sep;

    function isRulesetLikeNode(rule, root) {
         // if it has nested rules, then it should be treated like a ruleset
         // medias and comments do not have nested rules, but should be treated like rulesets anyway
         // some directives and anonymous nodes are ruleset like, others are not
         if (typeof rule.isRulesetLike === "boolean")
         {
             return rule.isRulesetLike;
         } else if (typeof rule.isRulesetLike === "function")
         {
             return rule.isRulesetLike(root);
         }

         //anything else is assumed to be a rule
         return false;
    }

    for (i = 0; i < this.rules.length; i++) {
        rule = this.rules[i];
        if (isRulesetLikeNode(rule, this.root)) {
            rulesetNodes.push(rule);
        } else {
            //charsets should float on top of everything
            if (rule.isCharset && rule.isCharset()) {
                charsetRuleNodes.push(rule);
            } else {
                ruleNodes.push(rule);
            }
        }
    }
    ruleNodes = charsetRuleNodes.concat(ruleNodes);

    // If this is the root node, we don't render
    // a selector, or {}.
    if (!this.root) {
        debugInfo = getDebugInfo(context, this, tabSetStr);

        if (debugInfo) {
            output.add(debugInfo);
            output.add(tabSetStr);
        }

        var paths = this.paths, pathCnt = paths.length,
            pathSubCnt;

        sep = context.compress ? ',' : (',\n' + tabSetStr);

        for (i = 0; i < pathCnt; i++) {
            path = paths[i];
            if (!(pathSubCnt = path.length)) { continue; }
            if (i > 0) { output.add(sep); }

            context.firstSelector = true;
            path[0].genCSS(context, output);

            context.firstSelector = false;
            for (j = 1; j < pathSubCnt; j++) {
                path[j].genCSS(context, output);
            }
        }

        output.add((context.compress ? '{' : ' {\n') + tabRuleStr);
    }

    // Compile rules and rulesets
    for (i = 0; i < ruleNodes.length; i++) {
        rule = ruleNodes[i];

        // @page{ directive ends up with root elements inside it, a mix of rules and rulesets
        // In this instance we do not know whether it is the last property
        if (i + 1 === ruleNodes.length && (!this.root || rulesetNodes.length === 0 || this.firstRoot)) {
            context.lastRule = true;
        }

        if (rule.genCSS) {
            rule.genCSS(context, output);
        } else if (rule.value) {
            output.add(rule.value.toString());
        }

        if (!context.lastRule) {
            output.add(context.compress ? '' : ('\n' + tabRuleStr));
        } else {
            context.lastRule = false;
        }
    }

    if (!this.root) {
        output.add((context.compress ? '}' : '\n' + tabSetStr + '}'));
        context.tabLevel--;
    }

    sep = (context.compress ? "" : "\n") + (this.root ? tabRuleStr : tabSetStr);
    rulesetNodeCnt = rulesetNodes.length;
    if (rulesetNodeCnt) {
        if (ruleNodes.length && sep) { output.add(sep); }
        rulesetNodes[0].genCSS(context, output);
        for (i = 1; i < rulesetNodeCnt; i++) {
            if (sep) { output.add(sep); }
            rulesetNodes[i].genCSS(context, output);
        }
    }

    if (!output.isEmpty() && !context.compress && this.firstRoot) {
        output.add('\n');
    }
};
Ruleset.prototype.markReferenced = function () {
    if (!this.selectors) {
        return;
    }
    for (var s = 0; s < this.selectors.length; s++) {
        this.selectors[s].markReferenced();
    }
};
Ruleset.prototype.joinSelectors = function (paths, context, selectors) {
    for (var s = 0; s < selectors.length; s++) {
        this.joinSelector(paths, context, selectors[s]);
    }
};
Ruleset.prototype.joinSelector = function (paths, context, selector) {

    var i, j, k,
        hasParentSelector, newSelectors, el, sel, parentSel,
        newSelectorPath, afterParentJoin, newJoinedSelector,
        newJoinedSelectorEmpty, lastSelector, currentElements,
        selectorsMultiplied;

    for (i = 0; i < selector.elements.length; i++) {
        el = selector.elements[i];
        if (el.value === '&') {
            hasParentSelector = true;
        }
    }

    if (!hasParentSelector) {
        if (context.length > 0) {
            for (i = 0; i < context.length; i++) {
                paths.push(context[i].concat(selector));
            }
        }
        else {
            paths.push([selector]);
        }
        return;
    }

    // The paths are [[Selector]]
    // The first list is a list of comma separated selectors
    // The inner list is a list of inheritance separated selectors
    // e.g.
    // .a, .b {
    //   .c {
    //   }
    // }
    // == [[.a] [.c]] [[.b] [.c]]
    //

    // the elements from the current selector so far
    currentElements = [];
    // the current list of new selectors to add to the path.
    // We will build it up. We initiate it with one empty selector as we "multiply" the new selectors
    // by the parents
    newSelectors = [[]];

    for (i = 0; i < selector.elements.length; i++) {
        el = selector.elements[i];
        // non parent reference elements just get added
        if (el.value !== "&") {
            currentElements.push(el);
        } else {
            // the new list of selectors to add
            selectorsMultiplied = [];

            // merge the current list of non parent selector elements
            // on to the current list of selectors to add
            if (currentElements.length > 0) {
                this.mergeElementsOnToSelectors(currentElements, newSelectors);
            }

            // loop through our current selectors
            for (j = 0; j < newSelectors.length; j++) {
                sel = newSelectors[j];
                // if we don't have any parent paths, the & might be in a mixin so that it can be used
                // whether there are parents or not
                if (context.length === 0) {
                    // the combinator used on el should now be applied to the next element instead so that
                    // it is not lost
                    if (sel.length > 0) {
                        sel[0].elements = sel[0].elements.slice(0);
                        sel[0].elements.push(new Element(el.combinator, '', el.index, el.currentFileInfo));
                    }
                    selectorsMultiplied.push(sel);
                }
                else {
                    // and the parent selectors
                    for (k = 0; k < context.length; k++) {
                        parentSel = context[k];
                        // We need to put the current selectors
                        // then join the last selector's elements on to the parents selectors

                        // our new selector path
                        newSelectorPath = [];
                        // selectors from the parent after the join
                        afterParentJoin = [];
                        newJoinedSelectorEmpty = true;

                        //construct the joined selector - if & is the first thing this will be empty,
                        // if not newJoinedSelector will be the last set of elements in the selector
                        if (sel.length > 0) {
                            newSelectorPath = sel.slice(0);
                            lastSelector = newSelectorPath.pop();
                            newJoinedSelector = selector.createDerived(lastSelector.elements.slice(0));
                            newJoinedSelectorEmpty = false;
                        }
                        else {
                            newJoinedSelector = selector.createDerived([]);
                        }

                        //put together the parent selectors after the join
                        if (parentSel.length > 1) {
                            afterParentJoin = afterParentJoin.concat(parentSel.slice(1));
                        }

                        if (parentSel.length > 0) {
                            newJoinedSelectorEmpty = false;

                            // /deep/ is a combinator that is valid without anything in front of it
                            // so if the & does not have a combinator that is "" or " " then
                            // and there is a combinator on the parent, then grab that.
                            // this also allows + a { & .b { .a & { ... though not sure why you would want to do that
                            var combinator = el.combinator,
                                parentEl = parentSel[0].elements[0];
                            if (combinator.emptyOrWhitespace && !parentEl.combinator.emptyOrWhitespace) {
                                combinator = parentEl.combinator;
                            }
                            // join the elements so far with the first part of the parent
                            newJoinedSelector.elements.push(new Element(combinator, parentEl.value, el.index, el.currentFileInfo));
                            newJoinedSelector.elements = newJoinedSelector.elements.concat(parentSel[0].elements.slice(1));
                        }

                        if (!newJoinedSelectorEmpty) {
                            // now add the joined selector
                            newSelectorPath.push(newJoinedSelector);
                        }

                        // and the rest of the parent
                        newSelectorPath = newSelectorPath.concat(afterParentJoin);

                        // add that to our new set of selectors
                        selectorsMultiplied.push(newSelectorPath);
                    }
                }
            }

            // our new selectors has been multiplied, so reset the state
            newSelectors = selectorsMultiplied;
            currentElements = [];
        }
    }

    // if we have any elements left over (e.g. .a& .b == .b)
    // add them on to all the current selectors
    if (currentElements.length > 0) {
        this.mergeElementsOnToSelectors(currentElements, newSelectors);
    }

    for (i = 0; i < newSelectors.length; i++) {
        if (newSelectors[i].length > 0) {
            paths.push(newSelectors[i]);
        }
    }
};
Ruleset.prototype.mergeElementsOnToSelectors = function(elements, selectors) {
    var i, sel;

    if (selectors.length === 0) {
        selectors.push([ new Selector(elements) ]);
        return;
    }

    for (i = 0; i < selectors.length; i++) {
        sel = selectors[i];

        // if the previous thing in sel is a parent this needs to join on to it
        if (sel.length > 0) {
            sel[sel.length - 1] = sel[sel.length - 1].createDerived(sel[sel.length - 1].elements.concat(elements));
        }
        else {
            sel.push(new Selector(elements));
        }
    }
};
module.exports = Ruleset;
