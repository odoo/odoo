# Kodoo Mobile

Shell mobile oficial do `kodoo` para Android e iOS, usando `Capacitor` e carregando `https://kodoo.online` como origem principal. O backend continua sendo o Odoo do projeto.

## Decisao tecnica

Esta primeira versao usa um shell hibrido, nao um app nativo completo. O ganho imediato e:

- reaproveitar `kodoo.online` como fonte unica de UI e autenticacao;
- manter Android e iOS sincronizados com o mesmo fluxo de negocio;
- reduzir custo operacional enquanto o produto ainda esta em validacao.

Limite objetivo: app stores costumam exigir algum valor nativo adicional. Antes de submissao ampla, vale incluir pelo menos camera/upload nativo, push notifications, biometria ou compartilhamento de arquivos.

## Requisitos

- Node.js 20+
- npm 10+
- Android Studio para Android
- Xcode 16+ em macOS para iOS

## Bootstrap

```bash
cd mobile/kodoo-capacitor
npm install
npm run add:android
npm run add:ios
npm run sync
```

Depois abra o projeto nativo:

```bash
npm run open:android
npm run open:ios
```

## URL do app

Por padrao, o shell aponta para:

```bash
https://kodoo.online
```

Para testar outra origem:

```bash
KODOO_APP_URL=https://staging.kodoo.online npm run sync
```

## Estrutura

- `capacitor.config.ts`: identidade do app e URL remota.
- `www/`: fallback minimo local usado pelo shell.
- `package.json`: comandos de sync, open e run.

## Proximos passos recomendados

1. Gerar os projetos `android/` e `ios/`.
2. Definir `appId` final e pacote de assinatura.
3. Criar icones, splash e nome final nas lojas.
4. Adicionar um primeiro recurso nativo real antes da publicacao.
