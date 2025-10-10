# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Página anterior
pdfjs-previous-button-label = Anterior
pdfjs-next-button =
    .title = Página seguinte
pdfjs-next-button-label = Seguinte
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
    .title = Trocar para o modo de apresentação
pdfjs-presentation-mode-button-label = Modo de apresentação
pdfjs-open-file-button =
    .title = Abrir ficheiro
pdfjs-open-file-button-label = Abrir
pdfjs-print-button =
    .title = Imprimir
pdfjs-print-button-label = Imprimir
pdfjs-save-button =
    .title = Guardar
pdfjs-save-button-label = Guardar
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Transferir
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Transferir
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
    .title = Rodar à direita
pdfjs-page-rotate-cw-button-label = Rodar à direita
pdfjs-page-rotate-ccw-button =
    .title = Rodar à esquerda
pdfjs-page-rotate-ccw-button-label = Rodar à esquerda
pdfjs-cursor-text-select-tool-button =
    .title = Ativar ferramenta de seleção de texto
pdfjs-cursor-text-select-tool-button-label = Ferramenta de seleção de texto
pdfjs-cursor-hand-tool-button =
    .title = Ativar ferramenta de mão
pdfjs-cursor-hand-tool-button-label = Ferramenta de mão
pdfjs-scroll-page-button =
    .title = Utilizar deslocamento da página
pdfjs-scroll-page-button-label = Deslocamento da página
pdfjs-scroll-vertical-button =
    .title = Utilizar deslocação vertical
pdfjs-scroll-vertical-button-label = Deslocação vertical
pdfjs-scroll-horizontal-button =
    .title = Utilizar deslocação horizontal
pdfjs-scroll-horizontal-button-label = Deslocação horizontal
pdfjs-scroll-wrapped-button =
    .title = Utilizar deslocação encapsulada
pdfjs-scroll-wrapped-button-label = Deslocação encapsulada
pdfjs-spread-none-button =
    .title = Não juntar páginas dispersas
pdfjs-spread-none-button-label = Sem spreads
pdfjs-spread-odd-button =
    .title = Juntar páginas dispersas a partir de páginas com números ímpares
pdfjs-spread-odd-button-label = Spreads ímpares
pdfjs-spread-even-button =
    .title = Juntar páginas dispersas a partir de páginas com números pares
pdfjs-spread-even-button-label = Spreads pares

## Document properties dialog

pdfjs-document-properties-button =
    .title = Propriedades do documento…
pdfjs-document-properties-button-label = Propriedades do documento…
pdfjs-document-properties-file-name = Nome do ficheiro:
pdfjs-document-properties-file-size = Tamanho do ficheiro:
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bytes)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bytes)
# Variables:
#   $size_kb (Number) - the PDF file size in kilobytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-kb = { $size_kb } KB ({ $size_b } bytes)
# Variables:
#   $size_mb (Number) - the PDF file size in megabytes
#   $size_b (Number) - the PDF file size in bytes
pdfjs-document-properties-mb = { $size_mb } MB ({ $size_b } bytes)
pdfjs-document-properties-title = Título:
pdfjs-document-properties-author = Autor:
pdfjs-document-properties-subject = Assunto:
pdfjs-document-properties-keywords = Palavras-chave:
pdfjs-document-properties-creation-date = Data de criação:
pdfjs-document-properties-modification-date = Data de modificação:
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $date (Date) - the creation/modification date of the PDF file
#   $time (Time) - the creation/modification time of the PDF file
pdfjs-document-properties-date-string = { $date }, { $time }
pdfjs-document-properties-creator = Criador:
pdfjs-document-properties-producer = Produtor de PDF:
pdfjs-document-properties-version = Versão do PDF:
pdfjs-document-properties-page-count = N.º de páginas:
pdfjs-document-properties-page-size = Tamanho da página:
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = retrato
pdfjs-document-properties-page-size-orientation-landscape = paisagem
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = Carta
pdfjs-document-properties-page-size-name-legal = Legal

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
pdfjs-document-properties-linearized = Vista rápida web:
pdfjs-document-properties-linearized-yes = Sim
pdfjs-document-properties-linearized-no = Não
pdfjs-document-properties-close-button = Fechar

## Print

pdfjs-print-progress-message = A preparar o documento para impressão…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress }%
pdfjs-print-progress-close-button = Cancelar
pdfjs-printing-not-supported = Aviso: a impressão não é totalmente suportada por este navegador.
pdfjs-printing-not-ready = Aviso: o PDF ainda não está totalmente carregado.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-toggle-sidebar-button =
    .title = Alternar barra lateral
pdfjs-toggle-sidebar-notification-button =
    .title = Alternar barra lateral (o documento contém contornos/anexos/camadas)
pdfjs-toggle-sidebar-button-label = Alternar barra lateral
pdfjs-document-outline-button =
    .title = Mostrar esquema do documento (duplo clique para expandir/colapsar todos os itens)
pdfjs-document-outline-button-label = Esquema do documento
pdfjs-attachments-button =
    .title = Mostrar anexos
pdfjs-attachments-button-label = Anexos
pdfjs-layers-button =
    .title = Mostrar camadas (clique duas vezes para repor todas as camadas para o estado predefinido)
pdfjs-layers-button-label = Camadas
pdfjs-thumbs-button =
    .title = Mostrar miniaturas
pdfjs-thumbs-button-label = Miniaturas
pdfjs-current-outline-item-button =
    .title = Encontrar o item atualmente destacado
pdfjs-current-outline-item-button-label = Item atualmente destacado
pdfjs-findbar-button =
    .title = Localizar em documento
pdfjs-findbar-button-label = Localizar
pdfjs-additional-layers = Camadas adicionais

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-title =
    .title = Página { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Miniatura da página { $page }

## Find panel button title and messages

pdfjs-find-input =
    .title = Localizar
    .placeholder = Localizar em documento…
pdfjs-find-previous-button =
    .title = Localizar ocorrência anterior da frase
pdfjs-find-previous-button-label = Anterior
pdfjs-find-next-button =
    .title = Localizar ocorrência seguinte da frase
pdfjs-find-next-button-label = Seguinte
pdfjs-find-highlight-checkbox = Destacar tudo
pdfjs-find-match-case-checkbox-label = Correspondência
pdfjs-find-match-diacritics-checkbox-label = Corresponder diacríticos
pdfjs-find-entire-word-checkbox-label = Palavras completas
pdfjs-find-reached-top = Topo do documento atingido, a continuar a partir do fundo
pdfjs-find-reached-bottom = Fim do documento atingido, a continuar a partir do topo
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count =
    { $total ->
        [one] { $current } de { $total } correspondência
       *[other] { $current } de { $total } correspondências
    }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [one] Mais de { $limit } correspondência
       *[other] Mais de { $limit } correspondências
    }
pdfjs-find-not-found = Frase não encontrada

## Predefined zoom values

pdfjs-page-scale-width = Ajustar à largura
pdfjs-page-scale-fit = Ajustar à página
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
pdfjs-invalid-file-error = Ficheiro PDF inválido ou danificado.
pdfjs-missing-file-error = Ficheiro PDF inexistente.
pdfjs-unexpected-response-error = Resposta inesperada do servidor.
pdfjs-rendering-error = Ocorreu um erro ao processar a página.

## Annotations

# Variables:
#   $date (Date) - the modification date of the annotation
#   $time (Time) - the modification time of the annotation
pdfjs-annotation-date-string = { $date }, { $time }
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

pdfjs-password-label = Introduza a palavra-passe para abrir este ficheiro PDF.
pdfjs-password-invalid = Palavra-passe inválida. Por favor, tente novamente.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Cancelar
pdfjs-web-fonts-disabled = Os tipos de letra web estão desativados: não é possível utilizar os tipos de letra PDF embutidos.

## Editing

pdfjs-editor-free-text-button =
    .title = Texto
pdfjs-editor-free-text-button-label = Texto
pdfjs-editor-ink-button =
    .title = Desenhar
pdfjs-editor-ink-button-label = Desenhar
pdfjs-editor-stamp-button =
    .title = Adicionar ou editar imagens
pdfjs-editor-stamp-button-label = Adicionar ou editar imagens
pdfjs-editor-highlight-button =
    .title = Destaque
pdfjs-editor-highlight-button-label = Destaque
pdfjs-highlight-floating-button1 =
    .title = Realçar
    .aria-label = Realçar
pdfjs-highlight-floating-button-label = Realçar
pdfjs-editor-signature-button =
    .title = Adicionar assinatura
pdfjs-editor-signature-button-label = Adicionar assinatura

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Editor de realce
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
    .title = Alterar espessura quando destacar itens que não sejam texto
pdfjs-editor-add-signature-container =
    .aria-label = Controlos de assinatura e assinaturas guardadas
pdfjs-editor-signature-add-signature-button =
    .title = Adicionar nova assinatura
pdfjs-editor-signature-add-signature-button-label = Adicionar nova assinatura
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Assinatura guardada: { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Editor de texto
    .default-content = Comece a escrever…
pdfjs-free-text =
    .aria-label = Editor de texto
pdfjs-free-text-default-content = Começar a digitar…
pdfjs-ink =
    .aria-label = Editor de desenho
pdfjs-ink-canvas =
    .aria-label = Imagem criada pelo utilizador

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Texto alternativo
pdfjs-editor-alt-text-edit-button =
    .aria-label = Editar texto alternativo
pdfjs-editor-alt-text-edit-button-label = Editar texto alternativo
pdfjs-editor-alt-text-dialog-label = Escolher uma opção
pdfjs-editor-alt-text-dialog-description = O texto alternativo (texto alternativo) ajuda quando as pessoas não conseguem ver a imagem ou quando a mesma não é carregada.
pdfjs-editor-alt-text-add-description-label = Adicionar uma descrição
pdfjs-editor-alt-text-add-description-description = Aponte para 1-2 frases que descrevam o assunto, definição ou ações.
pdfjs-editor-alt-text-mark-decorative-label = Marcar como decorativa
pdfjs-editor-alt-text-mark-decorative-description = Isto é utilizado para imagens decorativas, tais como limites ou marcas d'água.
pdfjs-editor-alt-text-cancel-button = Cancelar
pdfjs-editor-alt-text-save-button = Guardar
pdfjs-editor-alt-text-decorative-tooltip = Marcada como decorativa
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Por exemplo, “Um jovem senta-se à mesa para comer uma refeição”
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Texto alternativo

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-label-top-left = Canto superior esquerdo — redimensionar
pdfjs-editor-resizer-label-top-middle = Superior ao centro — redimensionar
pdfjs-editor-resizer-label-top-right = Canto superior direito — redimensionar
pdfjs-editor-resizer-label-middle-right = Centro à direita — redimensionar
pdfjs-editor-resizer-label-bottom-right = Canto inferior direito — redimensionar
pdfjs-editor-resizer-label-bottom-middle = Inferior ao centro — redimensionar
pdfjs-editor-resizer-label-bottom-left = Canto inferior esquerdo — redimensionar
pdfjs-editor-resizer-label-middle-left = Centro à esquerda — redimensionar
pdfjs-editor-resizer-top-left =
    .aria-label = Canto superior esquerdo — redimensionar
pdfjs-editor-resizer-top-middle =
    .aria-label = Superior ao centro — redimensionar
pdfjs-editor-resizer-top-right =
    .aria-label = Canto superior direito — redimensionar
pdfjs-editor-resizer-middle-right =
    .aria-label = Centro à direita — redimensionar
pdfjs-editor-resizer-bottom-right =
    .aria-label = Canto inferior direito — redimensionar
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Inferior ao centro — redimensionar
pdfjs-editor-resizer-bottom-left =
    .aria-label = Canto inferior esquerdo — redimensionar
pdfjs-editor-resizer-middle-left =
    .aria-label = Centro à esquerda — redimensionar

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Cor de destaque
pdfjs-editor-colorpicker-button =
    .title = Alterar cor
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Escolhas de cor
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

pdfjs-editor-highlight-show-all-button-label = Mostrar tudo
pdfjs-editor-highlight-show-all-button =
    .title = Mostrar tudo

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Editar texto alternativo (descrição da imagem)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Adicionar texto alternativo (descrição da imagem)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Escreva a sua descrição aqui…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Descrição curta para as pessoas que não podem visualizar a imagem ou quando a imagem não carrega.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Este texto alternativo foi criado automaticamente e pode ser impreciso.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = Saber mais
pdfjs-editor-new-alt-text-create-automatically-button-label = Criar texto alternativo automaticamente
pdfjs-editor-new-alt-text-not-now-button = Agora não
pdfjs-editor-new-alt-text-error-title = Não foi possível criar o texto alternativo automaticamente
pdfjs-editor-new-alt-text-error-description = Escreva o seu próprio texto alternativo ou tente novamente mais tarde.
pdfjs-editor-new-alt-text-error-close-button = Fechar
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = A transferir o modelo de IA de texto alternativo ({ $downloadedSize } de { $totalSize } MB)
    .aria-valuetext = A transferir o modelo de IA de texto alternativo ({ $downloadedSize } de { $totalSize } MB)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Texto alternativo adicionado
pdfjs-editor-new-alt-text-added-button-label = Texto alternativo adicionado
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Texto alternativo em falta
pdfjs-editor-new-alt-text-missing-button-label = Texto alternativo em falta
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Rever texto alternativo
pdfjs-editor-new-alt-text-to-review-button-label = Rever texto alternativo
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Criado automaticamente: { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Definições de texto alternativo da imagem
pdfjs-image-alt-text-settings-button-label = Definições de texto alternativo da imagem
pdfjs-editor-alt-text-settings-dialog-label = Definições de texto alternativo das imagens
pdfjs-editor-alt-text-settings-automatic-title = Texto alternativo automático
pdfjs-editor-alt-text-settings-create-model-button-label = Criar texto alternativo automaticamente
pdfjs-editor-alt-text-settings-create-model-description = Sugere descrições para ajudar as pessoas que não podem visualizar a imagem ou quando a imagem não carrega.
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
pdfjs-editor-alt-text-settings-download-model-label = Modelo de IA de texto alternativo ({ $totalSize } MB)
pdfjs-editor-alt-text-settings-ai-model-description = É executado localmente no seu dispositivo para que os seus dados se mantenham privados. É necessário para o texto alternativo automático.
pdfjs-editor-alt-text-settings-delete-model-button = Eliminar
pdfjs-editor-alt-text-settings-download-model-button = Transferir
pdfjs-editor-alt-text-settings-downloading-model-button = A transferir…
pdfjs-editor-alt-text-settings-editor-title = Editor de texto alternativo
pdfjs-editor-alt-text-settings-show-dialog-button-label = Mostrar editor de texto alternativo imediatamente ao adicionar uma imagem
pdfjs-editor-alt-text-settings-show-dialog-description = Ajuda a garantir que todas as suas imagens tenham um texto alternativo.
pdfjs-editor-alt-text-settings-close-button = Fechar

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Destaque removido
pdfjs-editor-undo-bar-message-freetext = Texto removido
pdfjs-editor-undo-bar-message-ink = Desenho removido
pdfjs-editor-undo-bar-message-stamp = Imagem removida
pdfjs-editor-undo-bar-message-signature = Assinatura removida
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } anotação removida
       *[other] { $count } anotações removidas
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Anular
pdfjs-editor-undo-bar-undo-button-label = Anular
pdfjs-editor-undo-bar-close-button =
    .title = Fechar
pdfjs-editor-undo-bar-close-button-label = Fechar

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Este modo permite ao utilizador criar uma assinatura para adicionar a um documento PDF. O utilizador pode editar o nome (que também funciona como texto alternativo) e, opcionalmente, guardar a assinatura para utilizações frequentes.
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
    .aria-label = Digite a sua assinatura
    .placeholder = Digite a sua assinatura
pdfjs-editor-add-signature-draw-placeholder = Desenhe a sua assinatura
pdfjs-editor-add-signature-draw-thickness-range-label = Espessura
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Espessura do desenho: { $thickness }
pdfjs-editor-add-signature-image-placeholder = Arraste um ficheiro aqui para carregar
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Ou escolha ficheiros de imagem
       *[other] Ou explore ficheiros de imagem
    }

## Controls

pdfjs-editor-add-signature-description-label = Descrição (texto alternativo)
pdfjs-editor-add-signature-description-input =
    .title = Descrição (texto alternativo)
pdfjs-editor-add-signature-description-default-when-drawing = Assinatura
pdfjs-editor-add-signature-clear-button-label = Limpar assinatura
pdfjs-editor-add-signature-clear-button =
    .title = Limpar assinatura
pdfjs-editor-add-signature-save-checkbox = Guardar assinatura
pdfjs-editor-add-signature-save-warning-message = Atingiu o limite de 5 assinaturas guardadas. Remova uma para guardar mais.
pdfjs-editor-add-signature-image-upload-error-title = Não foi possível carregar a imagem
pdfjs-editor-add-signature-image-upload-error-description = Verifique a sua ligação à rede ou tente outra imagem.
pdfjs-editor-add-signature-error-close-button = Fechar

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Cancelar
pdfjs-editor-add-signature-add-button = Adicionar
pdfjs-editor-edit-signature-update-button = Atualizar

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Remover assinatura guardada
pdfjs-editor-delete-signature-button-label1 = Remover assinatura guardada

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Editar descrição

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Editar descrição
