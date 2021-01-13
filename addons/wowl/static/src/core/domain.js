/** @odoo-module **/
import { evaluate, formatAST, parseExpr } from "../py/index";
import { toPyValue } from "../py/utils";
export class Domain {
  constructor(descr = []) {
    if (descr instanceof Domain) {
      this.ast = descr.ast;
    } else {
      const rawAST = typeof descr === "string" ? parseExpr(descr) : toAST(descr);
      this.ast = normalizeDomainAST(rawAST);
    }
  }
  contains(record) {
    const expr = evaluate(this.ast, record);
    return matchDomain(record, expr);
  }
  toString() {
    return formatAST(this.ast);
  }
  toList(context) {
    return evaluate(this.ast, context);
  }
}
export function combineDomains(domains, operator) {
  if (domains.length === 0) {
    return new Domain([]);
  }
  const domain1 = domains[0] instanceof Domain ? domains[0] : new Domain(domains[0]);
  if (domains.length === 1) {
    return domain1;
  }
  const domain2 = combineDomains(domains.slice(1), operator);
  const result = new Domain([]);
  const astValues1 = domain1.ast.value;
  const astValues2 = domain2.ast.value;
  const op = operator === "AND" ? "&" : "|";
  const combinedAST = { type: 4 /* List */, value: astValues1.concat(astValues2) };
  result.ast = normalizeDomainAST(combinedAST, op);
  return result;
}
function toAST(domain) {
  const elems = domain.map((elem) => {
    switch (elem) {
      case "!":
      case "&":
      case "|":
        return { type: 1 /* String */, value: elem };
      default:
        return {
          type: 10 /* Tuple */,
          value: elem.map(toPyValue),
        };
    }
  });
  return { type: 4 /* List */, value: elems };
}
function normalizeDomainAST(domain, op = "&") {
  if (domain.type !== 4 /* List */) {
    throw new Error("Invalid domain AST");
  }
  let expected = -1;
  for (let child of domain.value) {
    if (child.type === 1 /* String */ && (child.value === "&" || child.value === "|")) {
      expected--;
    } else if (child.type !== 1 /* String */ || child.value !== "!") {
      expected++;
    }
  }
  let values = domain.value.slice();
  while (expected > 0) {
    expected--;
    values.unshift({ type: 1 /* String */, value: op });
  }
  return { type: 4 /* List */, value: values };
}
function matchDomain(record, domain) {
  if (domain.length === 0) {
    return true;
  }
  switch (domain[0]) {
    case "!":
      return !matchDomain(record, domain.slice(1));
    case "&":
      return matchDomain(record, domain.slice(1, 2)) && matchDomain(record, domain.slice(2));
    case "|":
      return matchDomain(record, domain.slice(1, 2)) || matchDomain(record, domain.slice(2));
    default:
      const condition = domain[0];
      const field = condition[0];
      const fieldValue = record[field];
      const value = condition[2];
      switch (condition[1]) {
        case "=":
        case "==":
          return fieldValue === value;
        case "!=":
        case "<>":
          return fieldValue !== value;
        case "<":
          return fieldValue < value;
        case "<=":
          return fieldValue <= value;
        case ">":
          return fieldValue > value;
        case ">=":
          return fieldValue >= value;
        case "in":
          return value.includes(fieldValue);
        case "not in":
          return !value.includes(fieldValue);
        case "like":
          return fieldValue.toLowerCase().indexOf(value.toLowerCase()) >= 0;
        case "=like":
          const regExp = new RegExp(
            value
              .toLowerCase()
              .replace(/([.\[\]\{\}\+\*])/g, "\\$1")
              .replace(/%/g, ".*")
          );
          return regExp.test(fieldValue.toLowerCase());
        case "ilike":
          return fieldValue.indexOf(value) >= 0;
        case "=ilike":
          return new RegExp(value.replace(/%/g, ".*"), "i").test(fieldValue);
      }
  }
  throw new Error("could not match domain");
}
