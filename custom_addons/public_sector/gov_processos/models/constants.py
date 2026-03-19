PROCESS_TYPE_SELECTION = [
    ("compras_servicos", "Compras e Serviços"),
    ("obras_engenharia", "Obras e Engenharia"),
    ("tic", "Tecnologia da Informação"),
    ("contratacao_direta", "Contratação Direta"),
    ("urgencia_emergencia", "Urgência / Emergência"),
    ("outros", "Outros"),
]

PROCESS_SCOPE_SELECTION = [
    ("compras", "Compras"),
    ("servicos", "Serviços"),
    ("servicos_continuados", "Serviços de Prestação Continuada"),
]

TEMPLATE_SCOPE_SELECTION = [
    ("all", "Todos os Escopos"),
    ("compras", "Compras"),
    ("servicos", "Serviços"),
    ("servicos_continuados", "Serviços de Prestação Continuada"),
]

AI_PROVIDER_SELECTION = [
    ("odoo_chat", "Odoo Chat (Interno)"),
    ("openai", "OpenAI (ChatGPT)"),
    ("anthropic", "Anthropic (Claude)"),
    ("huggingface", "Hugging Face (LangChain)"),
    ("ollama", "Ollama Local"),
]

DOC_TYPE_SELECTION = [
    ("dfd", "DFD — Formalização de Demanda"),
    ("etp", "ETP — Estudo Técnico Preliminar"),
    ("tr", "TR — Termo de Referência"),
    ("edital", "Edital"),
    ("contrato", "Contrato"),
    ("nf", "Nota Fiscal"),
    ("despacho", "Despacho"),
    ("os", "Ordem de Serviço"),
    ("prestacao", "Prestação de Contas"),
    ("outro", "Outro"),
]

XLSX_PROFILE_SELECTION = [
    ("procurement_reference", "Compras / Pesquisa de Preços"),
    ("service_continuous_labor", "Serviços Continuados com Mão de Obra"),
]
