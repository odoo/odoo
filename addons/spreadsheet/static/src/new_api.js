const pivot = {
  model: "partner",
  domain: [],
  id: "1",
  context: {},
  measures: ["probability"],
  colGroupBys: [],
  rowGroupBys: ["date"],
  name: "Partners by Date",
  order: "ASC", // || undefined || "DESC"
}

const list = {
  model: "partner",
  domain: [],
  id: "1",
  context: {},
  columns: ["name", "email"],
  orderBy: [{field: "probability", asc: true}, {field: "name", asc: false}], // || null
}

const chart = {
type: "odoo_line",
title: "Contact",
legendPosition: "top",
definition: {
  model: "partner",
  domain: [],
  id: "1",
  context: {},
  measure: "debit_limit",
  order: "ASC", // || undefined || "DESC"
},
verticalAxisPosition: "left",
stacked: True,
}

const globalFilter = {
id: "122",
model: "res.users",
type: "relation",
label: "country",
// ... a million other things
}