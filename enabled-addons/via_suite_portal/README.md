# ViaSuite Portal

Módulo de gerenciamento central e orquestração do ecossistema **ViaSuite**.

## Visão Geral

O **ViaSuite Portal** atua como o "Cérebro" e "Despachante" da arquitetura multi-tenant. Ele deve ser instalado **exclusivamente** no banco de dados de gerenciamento (ex: `via-suite-viafronteira`).

## Funcionalidades Principais

### 1. Despachante Global (Dispatcher)
Gerencia o fluxo inicial de login no domínio raiz (`viafronteira.app`).
- **Roteamento Inteligente**: Detecta o claim `tenant` no token do Keycloak e despacha o usuário para o subdomínio correto.
- **Checagem de Status**: Valida se o tenant está `Active` antes de permitir o redirecionamento.
- **Bloqueio de Inativos**: Usuários de ambientes desativados são barrados com uma tela de "Ambiente Suspenso".

### 2. Orquestração de Bancos de Dados (DB Automation)
Automatiza o ciclo de vida físico dos tenants no PostgreSQL:
- **Zero-Touch Provisioning**: Ao salvar um novo registro de Tenant, o portal clona automaticamente o banco `via-suite-template` para criar o novo ambiente.
- **Renomeação Dinâmica**: Alterar o subdomínio no portal renomeia fisicamente o banco de dados no PostgreSQL.
- **Limpeza Automática**: Deletar um registro de Tenant executa o `DROP DATABASE` físico no servidor.

### 3. Segurança e Controle de Acesso
- **Trava de Instalação**: Possui um `pre_init_hook` que impede a instalação do módulo em bancos que não sejam o de gerenciamento autorizado.
- **Gestão de Parâmetros**: Configuração central do banco molde via System Parameter `via_suite.template_database`.

## Configuração

### Variáveis de Ambiente
| Variável | Descrição | Exemplo |
| :--- | :--- | :--- |
| `VIA_SUITE_GLOBAL_DOMAIN` | Domínio base para o dispatcher | `viafronteira.app` |
| `VIA_SUITE_MANAGEMENT_DB` | Nome do banco autorizado para instalação | `via-suite-viafronteira` |

### Parâmetros de Sistema (Odoo)
| Parâmetro | Função | Default |
| :--- | :--- | :--- |
| `via_suite.template_database` | Banco de dados usado como molde para novos tenants | `via-suite-template` |

## Requisitos de Infraestrutura
Para que a orquestração física funcione, o usuário do banco de dados utilizado pelo Odoo no PostgreSQL deve possuir a permissão `CREATEDB`.

---
© 2026 ViaFronteira, LLC.
