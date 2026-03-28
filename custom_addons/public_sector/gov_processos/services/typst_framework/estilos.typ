#set page(
  paper: "a4",
  margin: (x: 2.5cm, y: 2.5cm),
)

#set text(
  font: "Libertinus Serif",
  size: 11pt,
  lang: "pt",
  fallback: true,
)

#set par(
  justify: true,
  leading: 1.35em,
)

#show heading.where(level: 1): it => block(above: 1.2em, below: 0.5em)[
  #text(size: 13pt, weight: "bold")[#it.body]
  #line(length: 100%, stroke: 0.7pt)
]

#set page(
  footer: context [
    #align(center)[
      Pagina #counter(page).display()
    ]
  ]
)
