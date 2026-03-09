# Dev Host Mode

Modo leve para desenvolver o `kodoo` sem subir o container completo do Odoo.

## Estrategia

- Odoo roda no host Arch Linux.
- PostgreSQL roda no host Arch Linux.
- Bases locais padrao:
  - `kodoo`: desenvolvimento principal
  - `ktest`: restauracao de backup e testes

Essa abordagem reduz custo de CPU/RAM e evita o ciclo lento de rebuild do container do app.

## Fluxo recomendado

1. Criar o arquivo local de ambiente, se ainda nao existir:

```bash
make env-init
```

Preencha `.env.make`, principalmente:

- `PG_LOCAL_PASSWORD`
- `DEV_HOST_ADMIN_PASSWORD`

2. Gerar a configuracao local do Odoo:

```bash
make dev-host-config
```

3. Preparar PostgreSQL local:

```bash
make dev-host-db-setup
```

4. Inicializar a base principal, se ainda estiver vazia:

```bash
make dev-host-db-init
```

5. Subir Odoo local:

```bash
make dev-host-up
```

6. Fazer backup e renovar `ktest`:

```bash
make dev-host-backup
make dev-host-restore-ktest
```

## Observacao

Para protecao de dados, trate `ktest` como destino de restore, nao como banco paralelo gravavel. Isso valida backup sem criar duas bases oficiais concorrentes.

O arquivo gerado `deploy/odoo/kodoo.dev-host.local.conf` e local e nao deve ser commitado.
