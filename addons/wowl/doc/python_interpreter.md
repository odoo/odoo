# Python Interpreter

## Overview

The Odoo web client features a built-in small python interpreter. Its purpose
is to evaluate small python expressions. This is important, because views in
Odoo have modifiers written in python, but they need to be evaluated by the
browser.

Example:

```js
evaluate("1 + 2*{'a': 1}.get('b', 54) + v", { v: 33 }); // returns 142
```

## API

The `py` javascript code exports 5 functions:

| Function                          | Description                                |
| --------------------------------- | ------------------------------------------ |
| tokenize(expr: string) -> Token[] | convert a string into a list of tokens     |
| parse(tokens: Token[]) -> AST     | parse a list of tokens into an AST         |
| parseExpr(expr: string) -> AST    | tokenize and parse an expression           |
| evaluate(ast: AST) -> any         | evaluate an AST                            |
| evaluateExpr(expr: string) -> any | tokenize, parse and evaluate an expression |
