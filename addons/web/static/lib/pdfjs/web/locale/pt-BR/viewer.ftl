# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Página anterior
pdfjs-previous-button-label = Anterior
pdfjs-next-button =
    .title = Próxima página
pdfjs-next-button-label = Próxima
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Página
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = de { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } de { $pagesCount })
pdfjs-zoom-out-button =
    .title = Reduzir
pdfjs-zoom-out-button-label = Reduzir
pdfjs-zoom-in-button =
    .title = Ampliar
pdfjs-zoom-in-button-label = Ampliar
pdfjs-zoom-select =
    .title = Zoom
pdfjs-presentation-mode-button =
    .title = Mudar para o modo de apresentação
pdfjs-presentation-mode-button-label = Modo de apresentação
pdfjs-open-file-button =
    .title = Abrir arquivo
pdfjs-open-file-button-label = Abrir
pdfjs-print-button =
    .title = Imprimir
pdfjs-print-button-label = Imprimir
pdfjs-save-button =
    .title = Salvar
pdfjs-save-button-label = Salvar
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Baixar
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Baixar
pdfjs-bookmark-button =
    .title = Página atual (ver URL da página atual)
pdfjs-bookmark-button-label = Pagina atual

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Ferramentas
pdfjs-tools-button-label = Ferramentas
pdfjs-first-page-button =
    .title = Ir para a primeira página
pdfjs-first-page-button-label = Ir para a primeira página
pdfjs-last-page-button =
    .title = Ir para a última página
pdfjs-last-page-button-label = Ir para a última página
pdfjs-page-rotate-cw-button =
    .title = Girar no sentido horário
pdfjs-page-rotate-cw-button-label = Girar no sentido horário
pdfjs-page-rotate-ccw-button =
    .title = Girar no sentido anti-horário
pdfjs-page-rotate-ccw-button-label = Girar no sentido anti-horário
pdfjs-cursor-text-select-tool-button =
    .title = Ativar a ferramenta de seleção de texto
pdfjs-cursor-text-select-tool-button-label = Ferramenta de seleção de texto
pdfjs-cursor-hand-tool-button =
    .title = Ativar ferramenta de deslocamento
pdfjs-cursor-hand-tool-button-label = Ferramenta de deslocamento
pdfjs-scroll-page-button =
    .title = Usar rolagem de página
pdfjs-scroll-page-button-label = Rolagem de página
pdfjs-scroll-vertical-button =
    .title = Usar deslocamento vertical
pdfjs-scroll-vertical-button-label = Deslocamento vertical
pdfjs-scroll-horizontal-button =
    .title = Usar deslocamento horizontal
pdfjs-scroll-horizontal-button-label = Deslocamento horizontal
pdfjs-scroll-wrapped-button =
    .title = Usar deslocamento contido
pdfjs-scroll-wrapped-button-label = Deslocamento contido
pdfjs-spread-none-button =
    .title = Não reagrupar páginas
pdfjs-spread-none-button-label = Não estender
pdfjs-spread-odd-button =
    .title = Agrupar páginas começando em páginas com números ímpares
pdfjs-spread-odd-button-label = Estender ímpares
pdfjs-spread-even-button =
    .title = Agrupar páginas começando em páginas com números pares
pdfjs-spread-even-button-label = Estender pares

## Document properties dialog

pdfjs-document-properties-button =
    .title = Propriedades do documento…
pdfjs-document-properties-button-label = Propriedades do documento…
pdfjs-document-properties-file-name = Nome do arquivo:
pdfjs-document-properties-file-size = Tamanho do arquivo:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bytes)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bytes)
pdfjs-document-properties-title = Título:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Assunto:
pdfjs-document-properties-keywords = Palavras-chave:
pdfjs-document-properties-creation-date = Data da criação:
pdfjs-document-properties-modification-date = Data da modificação:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Criação:
pdfjs-document-properties-producer = Criador do PDF:
pdfjs-document-properties-version = Versão do PDF:
pdfjs-document-properties-page-count = Número de páginas:
pdfjs-document-properties-page-size = Tamanho da página:
pdfjs-document-properties-page-size-unit-inches = pol.
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = retrato
pdfjs-document-properties-page-size-orientation-landscape = paisagem
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Carta
pdfjs-document-properties-page-size-name-legal = Jurídico

## Variables:
##   $width (Number) - the width of the (current) page
##   $height (Number) - the height of the (current) page
##   $unit (String) - the unit of measurement of the (current) page
##   $name (String) - the name of the (current) page
##   $orientation (String) - the orientation of the (current) page

pdfjs-document-properties-page-size-dimension-string = { $width } × { $height } { $unit } ({ $orientation })
pdfjs-document-properties-page-size-dimension-name-string = { $width } × { $height } { $unit } ({ $name }, { $orientation })

##

# The linearization status of the document; usually called "Fast Web View" in
# English locales of Adobe software.
pdfjs-document-properties-linearized = Exibição web rápida:
pdfjs-document-properties-linearized-yes = Sim
pdfjs-document-properties-linearized-no = Não
pdfjs-document-properties-close-button = Fechar
pdfjs-digital-signature-properties-view-certificate = Ver certificado
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Motivo: { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Data e hora: { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [one] Assinatura secundária ({ $count })
       *[other] Assinaturas secundárias ({ $count })
    }

## Print

pdfjs-print-progress-message = Preparando documento para impressão…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress } %
pdfjs-print-progress-close-button = Cancelar
pdfjs-printing-not-supported = Aviso: a impressão não é totalmente suportada neste navegador.
pdfjs-printing-not-ready = Aviso: o PDF não está totalmente carregado para impressão.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Encontrar item atual da estrutura
pdfjs-current-outline-item-button-label = Item atual da estrutura
pdfjs-findbar-button =
    .title = Procurar no documento
pdfjs-findbar-button-label = Procurar
pdfjs-additional-layers = Camadas adicionais

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatura da página { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Selecionar página { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Página { $page } de { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Procurar no documento…
    .title = Procurar
pdfjs-find-previous-button =
    .title = Procurar a ocorrência anterior da frase
pdfjs-find-previous-button-label = Anterior
pdfjs-find-next-button =
    .title = Procurar a próxima ocorrência da frase
pdfjs-find-next-button-label = Próxima
pdfjs-find-highlight-checkbox = Destacar tudo
pdfjs-find-match-case-checkbox-label = Diferenciar maiúsculas/minúsculas
pdfjs-find-match-diacritics-checkbox-label = Considerar acentuação
pdfjs-find-entire-word-checkbox-label = Palavras completas
pdfjs-find-reached-top = Início do documento alcançado, continuando do fim
pdfjs-find-reached-bottom = Fim do documento alcançado, continuando do início
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } de { $total } ocorrência
       *[other] { $current } de { $total } ocorrências
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Mais de { $limit } ocorrência
       *[other] Mais de { $limit } ocorrências
    }
pdfjs-find-not-found = Não encontrado

## Predefined zoom values

pdfjs-page-scale-width = Largura da página
pdfjs-page-scale-fit = Ajustar à janela
pdfjs-page-scale-auto = Zoom automático
pdfjs-page-scale-actual = Tamanho real
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale }%

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Página { $page }

## Loading indicator messages

pdfjs-loading-error = Ocorreu um erro ao carregar o PDF.
pdfjs-invalid-file-error = Arquivo PDF corrompido ou inválido.
pdfjs-missing-file-error = Arquivo PDF ausente.
pdfjs-unexpected-response-error = Resposta inesperada do servidor.
pdfjs-rendering-error = Ocorreu um erro ao renderizar a página.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [Anotação { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Forneça a senha para abrir este arquivo PDF.
pdfjs-password-invalid = Senha inválida. Tente novamente.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Cancelar
pdfjs-web-fonts-disabled = As fontes web estão desativadas: não foi possível usar fontes incorporadas do PDF.

## Editing

pdfjs-editor-free-text-button =
    .title = Texto
pdfjs-editor-color-picker-free-text-input =
    .title = Mudar cor do texto
pdfjs-editor-free-text-button-label = Texto
pdfjs-editor-ink-button =
    .title = Desenho
pdfjs-editor-color-picker-ink-input =
    .title = Mudar cor do desenho
pdfjs-editor-ink-button-label = Desenho
pdfjs-editor-stamp-button =
    .title = Adicionar ou editar imagens
pdfjs-editor-stamp-button-label = Adicionar ou editar imagens
pdfjs-editor-highlight-button =
    .title = Destaque
pdfjs-editor-highlight-button-label = Destaque
pdfjs-highlight-floating-button1 =
    .aria-label = Destaque
    .title = Destaque
pdfjs-highlight-floating-button-label = Destaque
pdfjs-comment-floating-button =
    .aria-label = Comentário
    .title = Comentário
pdfjs-comment-floating-button-label = Comentário
pdfjs-editor-comment-button =
    .aria-label = Comentar
    .title = Comentar
pdfjs-editor-comment-button-label = Comentar
pdfjs-editor-signature-button =
    .title = Adicionar assinatura
pdfjs-editor-signature-button-label = Adicionar assinatura

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Editor de destaque
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Editor de desenho
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Editor de assinatura: { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Editor de imagem

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Remover desenho
pdfjs-editor-remove-freetext-button =
    .title = Remover texto
pdfjs-editor-remove-stamp-button =
    .title = Remover imagem
pdfjs-editor-remove-highlight-button =
    .title = Remover destaque
pdfjs-editor-remove-signature-button =
    .title = Remover assinatura

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Cor
pdfjs-editor-free-text-size-input = Tamanho
pdfjs-editor-ink-color-input = Cor
pdfjs-editor-ink-thickness-input = Espessura
pdfjs-editor-ink-opacity-input = Opacidade
pdfjs-editor-stamp-add-image-button =
    .title = Adicionar imagem
pdfjs-editor-stamp-add-image-button-label = Adicionar imagem
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Espessura
pdfjs-editor-free-highlight-thickness-title =
    .title = Mudar espessura ao destacar itens que não são texto
pdfjs-editor-add-signature-container =
    .aria-label = Controles de assinatura e assinaturas salvas
pdfjs-editor-signature-add-signature-button =
    .title = Adicionar nova assinatura
pdfjs-editor-signature-add-signature-button-label = Adicionar nova assinatura
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Assinatura salva: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Editor de texto
    .default-content = Comece a digitar…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Comentário
       *[other] Comentários
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Fechar painel lateral
    .title = Fechar painel lateral
pdfjs-editor-comments-sidebar-close-button-label = Fechar painel lateral
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Viu algo digno de atenção? Destaque e deixe um comentário.
pdfjs-editor-comments-sidebar-no-comments-link = Saiba mais

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Texto alternativo
pdfjs-editor-alt-text-edit-button =
    .aria-label = Editar texto alternativo
pdfjs-editor-alt-text-dialog-label = Escolha uma opção
pdfjs-editor-alt-text-dialog-description = O texto alternativo ajuda quando uma imagem não aparece ou não é carregada.
pdfjs-editor-alt-text-add-description-label = Adicionar uma descrição
pdfjs-editor-alt-text-add-description-description = Procure usar uma ou duas frases que descrevam o assunto, cenário ou ação.
pdfjs-editor-alt-text-mark-decorative-label = Marcar como decorativa
pdfjs-editor-alt-text-mark-decorative-description = Isto é usado em imagens ornamentais, como bordas ou marcas d'água.
pdfjs-editor-alt-text-cancel-button = Cancelar
pdfjs-editor-alt-text-save-button = Salvar
pdfjs-editor-alt-text-decorative-tooltip = Marcado como decorativa
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Por exemplo, “Um jovem senta-se à mesa para comer uma refeição”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Texto alternativo

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Canto superior esquerdo — redimensionar
pdfjs-editor-resizer-top-middle =
    .aria-label = No centro do topo — redimensionar
pdfjs-editor-resizer-top-right =
    .aria-label = Canto superior direito — redimensionar
pdfjs-editor-resizer-middle-right =
    .aria-label = No meio à direita — redimensionar
pdfjs-editor-resizer-bottom-right =
    .aria-label = Canto inferior direito — redimensionar
pdfjs-editor-resizer-bottom-middle =
    .aria-label = No centro da base — redimensionar
pdfjs-editor-resizer-bottom-left =
    .aria-label = Canto inferior esquerdo — redimensionar
pdfjs-editor-resizer-middle-left =
    .aria-label = No meio à esquerda — redimensionar

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Cor de destaque
pdfjs-editor-colorpicker-button =
    .title = Mudar cor
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Opções de cores
pdfjs-editor-colorpicker-yellow =
    .title = Amarelo
pdfjs-editor-colorpicker-green =
    .title = Verde
pdfjs-editor-colorpicker-blue =
    .title = Azul
pdfjs-editor-colorpicker-pink =
    .title = Rosa
pdfjs-editor-colorpicker-red =
    .title = Vermelho

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Mostrar todos
pdfjs-editor-highlight-show-all-button =
    .title = Mostrar todos

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Editar texto alternativo (descrição da imagem)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Adicionar texto alternativo (descrição da imagem)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Você pode escrever uma descrição aqui…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Descrição curta para pessoas que não conseguem ver a imagem ou quando a imagem não é carregada.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Este texto alternativo foi criado automaticamente, pode não estar correto.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Saiba mais
pdfjs-editor-new-alt-text-create-automatically-button-label = Criar texto alternativo automaticamente
pdfjs-editor-new-alt-text-not-now-button = Agora não
pdfjs-editor-new-alt-text-error-title = Não foi possível criar texto alternativo automaticamente
pdfjs-editor-new-alt-text-error-description = Escreva seu próprio texto alternativo ou tente novamente mais tarde.
pdfjs-editor-new-alt-text-error-close-button = Fechar
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Baixando modelo de inteligência artificial de texto alternativo ({ $downloadedSize } de { $totalSize } MB)
    .aria-valuetext = Baixando modelo de inteligência artificial de texto alternativo ({ $downloadedSize } de { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Texto alternativo adicionado
pdfjs-editor-new-alt-text-added-button-label = Texto alternativo adicionado
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Sem texto alternativo
pdfjs-editor-new-alt-text-missing-button-label = Sem texto alternativo
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Revisar texto alternativo
pdfjs-editor-new-alt-text-to-review-button-label = Revisar texto alternativo
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Criado automaticamente: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Configurações de texto alternativo de imagens
pdfjs-image-alt-text-settings-button-label = Configurações de texto alternativo de imagens
pdfjs-editor-alt-text-settings-dialog-label = Configurações de texto alternativo de imagens
pdfjs-editor-alt-text-settings-automatic-title = Texto alternativo automático
pdfjs-editor-alt-text-settings-create-model-button-label = Criar texto alternativo automaticamente
pdfjs-editor-alt-text-settings-create-model-description = Sugere uma descrição para ajudar pessoas que não conseguem ver a imagem ou quando a imagem não é carregada.
pdfjs-editor-alt-text-settings-editor-title = Editor de texto alternativo
pdfjs-editor-alt-text-settings-show-dialog-button-label = Mostrar o editor de texto alternativo imediatamente ao adicionar uma imagem
pdfjs-editor-alt-text-settings-show-dialog-description = Ajuda a assegurar que todas as suas imagens tenham texto alternativo.
pdfjs-editor-alt-text-settings-close-button = Fechar

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Destaque adicionado
pdfjs-editor-freetext-added-alert = Texto adicionado
pdfjs-editor-ink-added-alert = Desenho adicionado
pdfjs-editor-stamp-added-alert = Imagem adicionada
pdfjs-editor-signature-added-alert = Assinatura adicionada

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Destaque removido
pdfjs-editor-undo-bar-message-freetext = Texto removido
pdfjs-editor-undo-bar-message-ink = Desenho removido
pdfjs-editor-undo-bar-message-stamp = Imagem removida
pdfjs-editor-undo-bar-message-signature = Assinatura removida
pdfjs-editor-undo-bar-message-comment = Comentário removido
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } anotação removida
       *[other] { $count } anotações removidas
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Desfazer
pdfjs-editor-undo-bar-undo-button-label = Desfazer
pdfjs-editor-undo-bar-close-button =
    .title = Fechar
pdfjs-editor-undo-bar-close-button-label = Fechar

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Esta janela permite ao usuário criar uma assinatura para adicionar a um documento PDF. O usuário pode editar o nome (que também serve como texto alternativo) e, opcionalmente, salvar a assinatura usar novamente.
pdfjs-editor-add-signature-dialog-title = Adicionar uma assinatura

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Digitar
    .title = Digitar
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Desenhar
    .title = Desenhar
pdfjs-editor-add-signature-image-button = Imagem
    .title = Imagem

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Digite sua assinatura
    .placeholder = Digite sua assinatura
pdfjs-editor-add-signature-draw-placeholder = Desenhe sua assinatura
pdfjs-editor-add-signature-draw-thickness-range-label = Espessura
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Espessura do desenho: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Arraste um arquivo aqui para enviar
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Ou escolha arquivos de imagem
       *[other] Ou escolha arquivos de imagem
    }

## Controls

pdfjs-editor-add-signature-description-label = Descrição (texto alternativo)
pdfjs-editor-add-signature-description-input =
    .title = Descrição (texto alternativo)
pdfjs-editor-add-signature-description-default-when-drawing = Assinatura
pdfjs-editor-add-signature-clear-button-label = Limpar assinatura
pdfjs-editor-add-signature-clear-button =
    .title = Limpar assinatura
pdfjs-editor-add-signature-save-checkbox = Salvar assinatura
pdfjs-editor-add-signature-save-warning-message = Você atingiu o limite de 5 assinaturas salvas. Remova uma para salvar mais.
pdfjs-editor-add-signature-image-upload-error-title = Não foi possível enviar a imagem
pdfjs-editor-add-signature-image-upload-error-description = Verifique sua conexão de rede ou tente outra imagem.
pdfjs-editor-add-signature-image-no-data-error-title = Não é possível converter esta imagem em uma assinatura
pdfjs-editor-add-signature-image-no-data-error-description = Experimente enviar outra imagem.
pdfjs-editor-add-signature-error-close-button = Fechar

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Cancelar
pdfjs-editor-add-signature-add-button = Adicionar
pdfjs-editor-edit-signature-update-button = Atualizar

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Editar comentário
pdfjs-editor-edit-comment-popup-button =
    .title = Editar comentário
pdfjs-editor-delete-comment-popup-button-label = Remover comentário
pdfjs-editor-delete-comment-popup-button =
    .title = Remover comentário
pdfjs-show-comment-button =
    .title = Mostrar comentário

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Editar comentário
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Atualizar
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Adicionar comentário
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Adicionar
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Começar a digitar…
pdfjs-editor-edit-comment-dialog-cancel-button = Cancelar

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Adicionar comentário

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Exibir/ocultar painel lateral (documento contém miniaturas/estrutura/anexos/camadas)
pdfjs-toggle-views-manager-button1-label = Gerenciar páginas
pdfjs-views-manager-sidebar =
    .aria-label = Painel lateral
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Redimensionador do painel lateral
pdfjs-views-manager-view-selector-button =
    .title = Exibição
pdfjs-views-manager-view-selector-button-label = Exibição
pdfjs-views-manager-pages-title = Páginas
pdfjs-views-manager-outlines-title1 = Estrutura do documento
    .title = Estrutura do documento (duplo clique para expandir/recolher todos os itens)
pdfjs-views-manager-attachments-title = Anexos
pdfjs-views-manager-layers-title1 = Camadas
    .title = Camadas (duplo clique para redefinir todas as camadas ao estado padrão)
pdfjs-views-manager-pages-option-label = Páginas
pdfjs-views-manager-outlines-option-label = Estrutura do documento
pdfjs-views-manager-attachments-option-label = Anexos
pdfjs-views-manager-layers-option-label = Camadas
pdfjs-views-manager-add-file-button =
    .title = Adicionar arquivo
pdfjs-views-manager-add-file-button-label = Adicionar arquivo
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } selecionada
       *[other] { $count } selecionadas
    }
pdfjs-views-manager-pages-status-none-action-label = Selecionar páginas
pdfjs-views-manager-pages-status-action-button-label = Gerenciar
pdfjs-views-manager-pages-status-copy-button-label = Copiar
pdfjs-views-manager-pages-status-cut-button-label = Cortar
pdfjs-views-manager-pages-status-delete-button-label = Excluir
pdfjs-views-manager-pages-status-export-selected-button-label = Exportar selecionados…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] 1 página cortada
       *[other] { $count } páginas cortadas
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] 1 página copiada
       *[other] { $count } páginas copiadas
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] 1 página excluída
       *[other] { $count } páginas excluídas
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Preparando seu arquivo…
pdfjs-views-manager-pages-status-waiting-uploading-label = Enviando arquivo…
pdfjs-views-manager-status-warning-cut-label = Não foi possível cortar. Atualize a página e tente novamente.
pdfjs-views-manager-status-warning-copy-label = Não foi possível copiar. Atualize a página e tente novamente.
pdfjs-views-manager-status-warning-delete-label = Não foi possível excluir. Atualize a página e tente novamente.
pdfjs-views-manager-status-warning-save-label = Não foi possível salvar. Atualize a página e tente novamente.
pdfjs-views-manager-status-undo-button-label = Desfazer
pdfjs-views-manager-status-done-button-label = Pronto
pdfjs-views-manager-status-close-button =
    .title = Fechar
pdfjs-views-manager-status-close-button-label = Fechar
pdfjs-views-manager-paste-button-label = Colar
pdfjs-views-manager-paste-button-before =
    .title = Colar antes da primeira página
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Colar após a página { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = NOVIDADE
pdfjs-views-manager-waiting-for-file = Enviando arquivo…
pdfjs-toggle-views-manager-button1 =
    .title = Gerenciar páginas

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = Propriedades da assinatura digital
    .title = Propriedades da assinatura digital
pdfjs-digital-signature-properties-button-label = Propriedades da assinatura digital

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = O documento foi assinado com uma assinatura digital válida
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [one] Documento assinado, mas { $count } assinatura digital não pôde ser verificada
       *[other] Documento assinado, mas { $count } assinaturas digitais não puderam ser verificadas
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [one] Documento assinado com { $count } certificado que não é confiável
       *[other] Documento assinado com { $count } certificados que não são confiáveis
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [one] Documento assinado com { $count } certificado expirado
       *[other] Documento assinado com { $count } certificados expirados
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [one] O documento tem { $count } assinatura digital inválida
       *[other] O documento tem { $count } assinaturas digitais inválidas
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [one] Documento assinado com { $count } certificado revogado
       *[other] Documento assinado com { $count } certificados revogados
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = Status: Assinatura verificada
pdfjs-digital-signature-properties-status-invalid = Status: Assinatura inválida
pdfjs-digital-signature-properties-status-unknown = Status: Não foi possível verificar (não há suporte)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = Certificado: Confiável ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = Certificado: Não disponível
pdfjs-digital-signature-properties-certificate-untrusted = Certificado: Não confiável
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Certificado: Emissor desconhecido ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = Certificado: Autoassinado ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Certificado: Emissor não confiável ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = Certificado: Expirado
pdfjs-digital-signature-properties-certificate-expired-with-date = Certificado: Expirado ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = Certificado: Revogado

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Remover assinatura salva
pdfjs-editor-delete-signature-button-label1 = Remover assinatura salva

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Mudar descrição

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Mudar descrição
