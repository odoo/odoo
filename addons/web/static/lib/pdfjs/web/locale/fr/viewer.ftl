# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


## Main toolbar buttons (tooltips and alt text for images)

pdfjs-previous-button =
    .title = Page précédente
pdfjs-previous-button-label = Précédent
pdfjs-next-button =
    .title = Page suivante
pdfjs-next-button-label = Suivant
# .title: Tooltip for the pageNumber input.
pdfjs-page-input =
    .title = Page
# Variables:
#   $pagesCount (Number) - the total number of pages in the document
# This string follows an input field with the number of the page currently displayed.
pdfjs-of-pages = sur { $pagesCount }
# Variables:
#   $pageNumber (Number) - the currently visible page
#   $pagesCount (Number) - the total number of pages in the document
pdfjs-page-of-pages = ({ $pageNumber } sur { $pagesCount })
pdfjs-zoom-out-button =
    .title = Zoom arrière
pdfjs-zoom-out-button-label = Zoom arrière
pdfjs-zoom-in-button =
    .title = Zoom avant
pdfjs-zoom-in-button-label = Zoom avant
pdfjs-zoom-select =
    .title = Zoom
pdfjs-presentation-mode-button =
    .title = Basculer en mode présentation
pdfjs-presentation-mode-button-label = Mode présentation
pdfjs-open-file-button =
    .title = Ouvrir le fichier
pdfjs-open-file-button-label = Ouvrir le fichier
pdfjs-print-button =
    .title = Imprimer
pdfjs-print-button-label = Imprimer
pdfjs-save-button =
    .title = Enregistrer
pdfjs-save-button-label = Enregistrer
# Used in Firefox for Android as a tooltip for the download button (“download” is a verb).
pdfjs-download-button =
    .title = Télécharger
# Used in Firefox for Android as a label for the download button (“download” is a verb).
# Length of the translation matters since we are in a mobile context, with limited screen estate.
pdfjs-download-button-label = Télécharger
pdfjs-bookmark-button =
    .title = Page courante (montrer l’adresse de la page courante)
pdfjs-bookmark-button-label = Page courante

##  Secondary toolbar and context menu

pdfjs-tools-button =
    .title = Outils
pdfjs-tools-button-label = Outils
pdfjs-first-page-button =
    .title = Aller à la première page
pdfjs-first-page-button-label = Aller à la première page
pdfjs-last-page-button =
    .title = Aller à la dernière page
pdfjs-last-page-button-label = Aller à la dernière page
pdfjs-page-rotate-cw-button =
    .title = Rotation horaire
pdfjs-page-rotate-cw-button-label = Rotation horaire
pdfjs-page-rotate-ccw-button =
    .title = Rotation antihoraire
pdfjs-page-rotate-ccw-button-label = Rotation antihoraire
pdfjs-cursor-text-select-tool-button =
    .title = Activer l’outil de sélection de texte
pdfjs-cursor-text-select-tool-button-label = Outil de sélection de texte
pdfjs-cursor-hand-tool-button =
    .title = Activer l’outil main
pdfjs-cursor-hand-tool-button-label = Outil main
pdfjs-scroll-page-button =
    .title = Utiliser le défilement par page
pdfjs-scroll-page-button-label = Défilement par page
pdfjs-scroll-vertical-button =
    .title = Utiliser le défilement vertical
pdfjs-scroll-vertical-button-label = Défilement vertical
pdfjs-scroll-horizontal-button =
    .title = Utiliser le défilement horizontal
pdfjs-scroll-horizontal-button-label = Défilement horizontal
pdfjs-scroll-wrapped-button =
    .title = Utiliser le défilement par bloc
pdfjs-scroll-wrapped-button-label = Défilement par bloc
pdfjs-spread-none-button =
    .title = Ne pas afficher les pages deux à deux
pdfjs-spread-none-button-label = Pas de double affichage
pdfjs-spread-odd-button =
    .title = Afficher les pages par deux, impaires à gauche
pdfjs-spread-odd-button-label = Doubles pages, impaires à gauche
pdfjs-spread-even-button =
    .title = Afficher les pages par deux, paires à gauche
pdfjs-spread-even-button-label = Doubles pages, paires à gauche

## Document properties dialog

pdfjs-document-properties-button =
    .title = Propriétés du document…
pdfjs-document-properties-button-label = Propriétés du document…
pdfjs-document-properties-file-name = Nom du fichier :
pdfjs-document-properties-file-size = Taille du fichier :
# Variables:
#   $kb (Number) - the PDF file size in kilobytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } Ko ({ $b } octets)
# Variables:
#   $mb (Number) - the PDF file size in megabytes
#   $b (Number) - the PDF file size in bytes
pdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } Mo ({ $b } octets)
pdfjs-document-properties-title = Titre :
pdfjs-document-properties-author = Auteur :
pdfjs-document-properties-subject = Sujet :
pdfjs-document-properties-keywords = Mots-clés :
pdfjs-document-properties-creation-date = Date de création :
pdfjs-document-properties-modification-date = Modifié le :
# Variables:
#   $dateObj (Date) - the creation/modification date and time of the PDF file
pdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
pdfjs-document-properties-creator = Créé par :
pdfjs-document-properties-producer = Outil de conversion PDF :
pdfjs-document-properties-version = Version PDF :
pdfjs-document-properties-page-count = Nombre de pages :
pdfjs-document-properties-page-size = Taille de la page :
pdfjs-document-properties-page-size-unit-inches = in
pdfjs-document-properties-page-size-unit-millimeters = mm
pdfjs-document-properties-page-size-orientation-portrait = portrait
pdfjs-document-properties-page-size-orientation-landscape = paysage
pdfjs-document-properties-page-size-name-a-three = A3
pdfjs-document-properties-page-size-name-a-four = A4
pdfjs-document-properties-page-size-name-letter = lettre
pdfjs-document-properties-page-size-name-legal = document juridique

## Variables:
##   $width (Number) - the width of the (current) page
##   $height (Number) - the height of the (current) page
##   $unit (String) - the unit of measurement of the (current) page
##   $name (String) - the name of the (current) page
##   $orientation (String) - the orientation of the (current) page

pdfjs-document-properties-page-size-dimension-string = { $width } × { $height } { $unit } ({ $orientation })
pdfjs-document-properties-page-size-dimension-name-string = { $width } × { $height } { $unit } ({ $name }, { $orientation })

##

# The linearization status of the document; usually called "Fast Web View" in
# English locales of Adobe software.
pdfjs-document-properties-linearized = Affichage rapide des pages web :
pdfjs-document-properties-linearized-yes = Oui
pdfjs-document-properties-linearized-no = Non
pdfjs-document-properties-close-button = Fermer
pdfjs-digital-signature-properties-view-certificate = Afficher le certificat
# Shown beneath an invalid signature card to explain why verification
# failed. The text comes from NSS (e.g. "Signature integrity has been
# compromised", "PKCS#7 signature could not be parsed") and is not
# itself localized — it is the underlying error message produced by
# the verification backend.
# Variables:
#   $reason (String) - error message describing why the signature
#                      could not be verified.
pdfjs-digital-signature-properties-reason = Raison : { $reason }
# Variables:
#   $dateObj (Date) - the signing time from the /Sig dict's /M entry.
pdfjs-digital-signature-properties-timestamp = Horodatage : { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }
# Variables:
#   $count (Number) - number of nested sub-signatures (one per earlier
#                     incremental revision of the document).
pdfjs-digital-signature-properties-sub-signatures =
    { $count ->
        [one] Sous-signature ({ $count })
       *[other] Sous-signatures ({ $count })
    }

## Print

pdfjs-print-progress-message = Préparation du document pour l’impression…
# Variables:
#   $progress (Number) - percent value
pdfjs-print-progress-percent = { $progress } %
pdfjs-print-progress-close-button = Annuler
pdfjs-printing-not-supported = Attention : l’impression n’est pas totalement prise en charge par ce navigateur.
pdfjs-printing-not-ready = Attention : le PDF n’est pas entièrement chargé pour pouvoir l’imprimer.

## Tooltips and alt text for side panel toolbar buttons

pdfjs-current-outline-item-button =
    .title = Trouver l’élément de plan actuel
pdfjs-current-outline-item-button-label = Élément de plan actuel
pdfjs-findbar-button =
    .title = Rechercher dans le document
pdfjs-findbar-button-label = Rechercher
pdfjs-additional-layers = Calques additionnels

## Thumbnails panel item (tooltip and alt text for images)

# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-canvas =
    .aria-label = Vignette de la page { $page }
# Variables:
#   $page (Number) - the page number
pdfjs-thumb-page-checkbox1 =
    .title = Sélectionner la page { $page }
# Variables:
#   $page (Number) - the page number
#   $total (Number) - the number of pages
pdfjs-thumb-page-title1 =
    .title = Page { $page } sur { $total }

## Find panel button title and messages

pdfjs-find-input =
    .placeholder = Rechercher dans le document…
    .title = Rechercher
pdfjs-find-previous-button =
    .title = Trouver l’occurrence précédente de l’expression
pdfjs-find-previous-button-label = Précédent
pdfjs-find-next-button =
    .title = Trouver la prochaine occurrence de l’expression
pdfjs-find-next-button-label = Suivant
pdfjs-find-highlight-checkbox = Tout surligner
pdfjs-find-match-case-checkbox-label = Respecter la casse
pdfjs-find-match-diacritics-checkbox-label = Respecter les accents et diacritiques
pdfjs-find-entire-word-checkbox-label = Mots entiers
pdfjs-find-reached-top = Haut de la page atteint, poursuite depuis la fin
pdfjs-find-reached-bottom = Bas de la page atteint, poursuite au début
# Variables:
#   $current (Number) - the index of the currently active find result
#   $total (Number) - the total number of matches in the document
pdfjs-find-match-count = Occurrence { $current } sur { $total }
# Variables:
#   $limit (Number) - the maximum number of matches
pdfjs-find-match-count-limit =
    { $limit ->
        [1] Plus d’une occurrence
       *[other] Plus de { $limit } occurrences
    }
pdfjs-find-not-found = Expression non trouvée

## Predefined zoom values

pdfjs-page-scale-width = Pleine largeur
pdfjs-page-scale-fit = Page entière
pdfjs-page-scale-auto = Zoom automatique
pdfjs-page-scale-actual = Taille réelle
# Variables:
#   $scale (Number) - percent value for page scale
pdfjs-page-scale-percent = { $scale } %

## PDF page

# Variables:
#   $page (Number) - the page number
pdfjs-page-landmark =
    .aria-label = Page { $page }

## Loading indicator messages

pdfjs-loading-error = Une erreur s’est produite lors du chargement du fichier PDF.
pdfjs-invalid-file-error = Fichier PDF invalide ou corrompu.
pdfjs-missing-file-error = Fichier PDF manquant.
pdfjs-unexpected-response-error = Réponse inattendue du serveur.
pdfjs-rendering-error = Une erreur s’est produite lors de l’affichage de la page.

## Annotations

# .alt: This is used as a tooltip.
# Variables:
#   $type (String) - an annotation type from a list defined in the PDF spec
# (32000-1:2008 Table 169 – Annotation types).
# Some common types are e.g.: "Check", "Text", "Comment", "Note"
pdfjs-text-annotation-type =
    .alt = [Annotation { $type }]
# Variables:
#   $dateObj (Date) - the modification date and time of the annotation
pdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: "short", timeStyle: "medium") }

## Password

pdfjs-password-label = Veuillez saisir le mot de passe pour ouvrir ce fichier PDF.
pdfjs-password-invalid = Mot de passe incorrect. Veuillez réessayer.
pdfjs-password-ok-button = OK
pdfjs-password-cancel-button = Annuler
pdfjs-web-fonts-disabled = Les polices web sont désactivées : impossible d’utiliser les polices intégrées au PDF.

## Editing

pdfjs-editor-free-text-button =
    .title = Texte
pdfjs-editor-color-picker-free-text-input =
    .title = Changer la couleur du texte
pdfjs-editor-free-text-button-label = Texte
pdfjs-editor-ink-button =
    .title = Dessiner
pdfjs-editor-color-picker-ink-input =
    .title = Changer la couleur pour dessiner
pdfjs-editor-ink-button-label = Dessiner
pdfjs-editor-stamp-button =
    .title = Ajouter ou modifier des images
pdfjs-editor-stamp-button-label = Ajouter ou modifier des images
pdfjs-editor-highlight-button =
    .title = Surligner
pdfjs-editor-highlight-button-label = Surligner
pdfjs-highlight-floating-button1 =
    .aria-label = Surligner
    .title = Surligner
pdfjs-highlight-floating-button-label = Surligner
pdfjs-comment-floating-button =
    .aria-label = Commenter
    .title = Commenter
pdfjs-comment-floating-button-label = Commenter
pdfjs-editor-comment-button =
    .aria-label = Commenter
    .title = Commenter
pdfjs-editor-comment-button-label = Commenter
pdfjs-editor-signature-button =
    .title = Ajouter une signature
pdfjs-editor-signature-button-label = Ajouter une signature

## Default editor aria labels

# “Highlight” is a noun, the string is used on the editor for highlights.
pdfjs-editor-highlight-editor =
    .aria-label = Éditeur de surlignage
# “Drawing” is a noun, the string is used on the editor for drawings.
pdfjs-editor-ink-editor =
    .aria-label = Éditeur de dessins
# Used when a signature editor is selected/hovered.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-signature-editor1 =
    .aria-description = Éditeur de signature : { $description }
pdfjs-editor-stamp-editor =
    .aria-label = Éditeur d’images

## Remove button for the various kind of editor.

pdfjs-editor-remove-ink-button =
    .title = Supprimer le dessin
pdfjs-editor-remove-freetext-button =
    .title = Supprimer le texte
pdfjs-editor-remove-stamp-button =
    .title = Supprimer l’image
pdfjs-editor-remove-highlight-button =
    .title = Supprimer le surlignage
pdfjs-editor-remove-signature-button =
    .title = Retirer la signature

##

# Editor Parameters
pdfjs-editor-free-text-color-input = Couleur
pdfjs-editor-free-text-size-input = Taille
pdfjs-editor-ink-color-input = Couleur
pdfjs-editor-ink-thickness-input = Épaisseur
pdfjs-editor-ink-opacity-input = Opacité
pdfjs-editor-stamp-add-image-button =
    .title = Ajouter une image
pdfjs-editor-stamp-add-image-button-label = Ajouter une image
# This refers to the thickness of the line used for free highlighting (not bound to text)
pdfjs-editor-free-highlight-thickness-input = Épaisseur
pdfjs-editor-free-highlight-thickness-title =
    .title = Modifier l’épaisseur pour le surlignage d’éléments non textuels
pdfjs-editor-add-signature-container =
    .aria-label = Contrôles de signature et signatures enregistrées
pdfjs-editor-signature-add-signature-button =
    .title = Ajouter une nouvelle signature
pdfjs-editor-signature-add-signature-button-label = Ajouter une nouvelle signature
# Used on the button to use an already saved signature.
# Variables:
#   $description (String) - a string describing/labeling the signature.
pdfjs-editor-add-saved-signature-button =
    .title = Signature enregistrée : { $description }
# .default-content is used as a placeholder in an empty text editor.
pdfjs-free-text2 =
    .aria-label = Éditeur de texte
    .default-content = Commencez à écrire…
# Used to show how many comments are present in the pdf file.
# Variables:
#   $count (Number) - the number of comments.
pdfjs-editor-comments-sidebar-title =
    { $count ->
        [one] Commentaire
       *[other] Commentaires
    }
pdfjs-editor-comments-sidebar-close-button =
    .aria-label = Fermer le panneau latéral
    .title = Fermer le panneau latéral
pdfjs-editor-comments-sidebar-close-button-label = Fermer le panneau latéral
# Instructional copy to add a comment by selecting text or an annotations.
pdfjs-editor-comments-sidebar-no-comments1 = Vous remarquez quelque chose d’intéressant ? Mettez-le en surbrillance et ajoutez un commentaire.
pdfjs-editor-comments-sidebar-no-comments-link = En savoir plus

## Alt-text dialog

pdfjs-editor-alt-text-button-label = Texte alternatif
pdfjs-editor-alt-text-edit-button =
    .aria-label = Modifier le texte alternatif
pdfjs-editor-alt-text-dialog-label = Sélectionnez une option
pdfjs-editor-alt-text-dialog-description = Le texte alternatif est utile lorsque des personnes ne peuvent pas voir l’image ou que l’image ne se charge pas.
pdfjs-editor-alt-text-add-description-label = Ajouter une description
pdfjs-editor-alt-text-add-description-description = Il est conseillé de rédiger une ou deux phrases décrivant le sujet, le cadre ou les actions.
pdfjs-editor-alt-text-mark-decorative-label = Marquer comme décorative
pdfjs-editor-alt-text-mark-decorative-description = Cette option est utilisée pour les images décoratives, comme les bordures ou les filigranes.
pdfjs-editor-alt-text-cancel-button = Annuler
pdfjs-editor-alt-text-save-button = Enregistrer
pdfjs-editor-alt-text-decorative-tooltip = Marquée comme décorative
# .placeholder: This is a placeholder for the alt text input area
pdfjs-editor-alt-text-textarea =
    .placeholder = Par exemple, « Un jeune homme est assis à une table pour prendre un repas »
# Alternative text (alt text) helps when people can't see the image.
pdfjs-editor-alt-text-button =
    .aria-label = Texte alternatif

## Editor resizers
## This is used in an aria label to help to understand the role of the resizer.

pdfjs-editor-resizer-top-left =
    .aria-label = Coin supérieur gauche — redimensionner
pdfjs-editor-resizer-top-middle =
    .aria-label = Milieu haut — redimensionner
pdfjs-editor-resizer-top-right =
    .aria-label = Coin supérieur droit — redimensionner
pdfjs-editor-resizer-middle-right =
    .aria-label = Milieu droit — redimensionner
pdfjs-editor-resizer-bottom-right =
    .aria-label = Coin inférieur droit — redimensionner
pdfjs-editor-resizer-bottom-middle =
    .aria-label = Centre bas — redimensionner
pdfjs-editor-resizer-bottom-left =
    .aria-label = Coin inférieur gauche — redimensionner
pdfjs-editor-resizer-middle-left =
    .aria-label = Milieu gauche — redimensionner

## Color picker

# This means "Color used to highlight text"
pdfjs-editor-highlight-colorpicker-label = Couleur de surlignage
pdfjs-editor-colorpicker-button =
    .title = Changer de couleur
pdfjs-editor-colorpicker-dropdown =
    .aria-label = Choix de couleurs
pdfjs-editor-colorpicker-yellow =
    .title = Jaune
pdfjs-editor-colorpicker-green =
    .title = Vert
pdfjs-editor-colorpicker-blue =
    .title = Bleu
pdfjs-editor-colorpicker-pink =
    .title = Rose
pdfjs-editor-colorpicker-red =
    .title = Rouge

## Show all highlights
## This is a toggle button to show/hide all the highlights.

pdfjs-editor-highlight-show-all-button-label = Tout afficher
pdfjs-editor-highlight-show-all-button =
    .title = Tout afficher

## New alt-text dialog
## Group note for entire feature: Alternative text (alt text) helps when people can't see the image. This feature includes a tool to create alt text automatically using an AI model that works locally on the user's device to preserve privacy.

# Modal header positioned above a text box where users can edit the alt text.
pdfjs-editor-new-alt-text-dialog-edit-label = Modifier le texte alternatif (description de l’image)
# Modal header positioned above a text box where users can add the alt text.
pdfjs-editor-new-alt-text-dialog-add-label = Ajouter du texte alternatif (description de l’image)
pdfjs-editor-new-alt-text-textarea =
    .placeholder = Rédigez votre description ici…
# This text refers to the alt text box above this description. It offers a definition of alt text.
pdfjs-editor-new-alt-text-description = Courte description pour les personnes qui ne peuvent pas voir l’image ou lorsque l’image ne se charge pas.
# This is a required legal disclaimer that refers to the automatically created text inside the alt text box above this text. It disappears if the text is edited by a human.
pdfjs-editor-new-alt-text-disclaimer1 = Ce texte alternatif a été créé automatiquement et peut être inexact.
pdfjs-editor-new-alt-text-disclaimer-learn-more-url = En savoir plus
pdfjs-editor-new-alt-text-create-automatically-button-label = Créer automatiquement le texte alternatif
pdfjs-editor-new-alt-text-not-now-button = Pas maintenant
pdfjs-editor-new-alt-text-error-title = Impossible de créer automatiquement le texte alternatif
pdfjs-editor-new-alt-text-error-description = Veuillez rédiger votre propre texte alternatif ou réessayer plus tard.
pdfjs-editor-new-alt-text-error-close-button = Fermer
# Variables:
#   $totalSize (Number) - the total size (in MB) of the AI model.
#   $downloadedSize (Number) - the downloaded size (in MB) of the AI model.
pdfjs-editor-new-alt-text-ai-model-downloading-progress = Téléchargement du modèle d’IA de texte alternatif ({ $downloadedSize } sur { $totalSize } Mo)
    .aria-valuetext = Téléchargement du modèle d’IA de texte alternatif ({ $downloadedSize } sur { $totalSize } Mo)
# This is a button that users can click to edit the alt text they have already added.
pdfjs-editor-new-alt-text-added-button =
    .aria-label = Texte alternatif ajouté
pdfjs-editor-new-alt-text-added-button-label = Texte alternatif ajouté
# This is a button that users can click to open the alt text editor and add alt text when it is not present.
pdfjs-editor-new-alt-text-missing-button =
    .aria-label = Texte alternatif manquant
pdfjs-editor-new-alt-text-missing-button-label = Texte alternatif manquant
# This is a button that opens up the alt text modal where users should review the alt text that was automatically generated.
pdfjs-editor-new-alt-text-to-review-button =
    .aria-label = Réviser le texte alternatif
pdfjs-editor-new-alt-text-to-review-button-label = Réviser le texte alternatif
# "Created automatically" is a prefix that will be added to the beginning of any alt text that has been automatically generated. After the colon, the user will see/hear the actual alt text description. If the alt text has been edited by a human, this prefix will not appear.
# Variables:
#   $generatedAltText (String) - the generated alt-text.
pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Créé automatiquement : { $generatedAltText }

## Image alt-text settings

pdfjs-image-alt-text-settings-button =
    .title = Paramètres du texte alternatif des images
pdfjs-image-alt-text-settings-button-label = Paramètres du texte alternatif des images
pdfjs-editor-alt-text-settings-dialog-label = Paramètres du texte alternatif des images
pdfjs-editor-alt-text-settings-automatic-title = Texte alternatif automatique
pdfjs-editor-alt-text-settings-create-model-button-label = Créer automatiquement le texte alternatif
pdfjs-editor-alt-text-settings-create-model-description = Suggère des descriptions pour aider les personnes qui ne peuvent pas voir l’image ou lorsque l’image ne se charge pas.
pdfjs-editor-alt-text-settings-editor-title = Éditeur de texte alternatif
pdfjs-editor-alt-text-settings-show-dialog-button-label = Afficher l’éditeur de texte alternatif immédiatement lors de l’ajout d’une image
pdfjs-editor-alt-text-settings-show-dialog-description = Vous aide à vous assurer que toutes vos images ont du texte alternatif.
pdfjs-editor-alt-text-settings-close-button = Fermer

## Accessibility labels (announced by screen readers) for objects added to the editor.

pdfjs-editor-highlight-added-alert = Surlignage ajouté
pdfjs-editor-freetext-added-alert = Texte ajouté
pdfjs-editor-ink-added-alert = Dessin ajouté
pdfjs-editor-stamp-added-alert = Image ajoutée
pdfjs-editor-signature-added-alert = Signature ajoutée

## "Annotations removed" bar

pdfjs-editor-undo-bar-message-highlight = Surlignage supprimé
pdfjs-editor-undo-bar-message-freetext = Texte supprimé
pdfjs-editor-undo-bar-message-ink = Dessin supprimé
pdfjs-editor-undo-bar-message-stamp = Image supprimée
pdfjs-editor-undo-bar-message-signature = Signature retirée
pdfjs-editor-undo-bar-message-comment = Commentaire supprimé
# Variables:
#   $count (Number) - the number of removed annotations.
pdfjs-editor-undo-bar-message-multiple =
    { $count ->
        [one] { $count } annotation supprimée
       *[other] { $count } annotations supprimées
    }
pdfjs-editor-undo-bar-undo-button =
    .title = Annuler
pdfjs-editor-undo-bar-undo-button-label = Annuler
pdfjs-editor-undo-bar-close-button =
    .title = Fermer
pdfjs-editor-undo-bar-close-button-label = Fermer

## Add a signature dialog

pdfjs-editor-add-signature-dialog-label = Cette fenêtre permet de créer une signature à ajouter à un document au format PDF. Il est possible d’en modifier le nom (qui sert également de texte alternatif) et, éventuellement, de l’enregistrer pour une utilisation répétée.
pdfjs-editor-add-signature-dialog-title = Ajout d’une signature

## Tab names

# Type is a verb (you can type your name as signature)
pdfjs-editor-add-signature-type-button = Saisir
    .title = Saisir au clavier
# Draw is a verb (you can draw your signature)
pdfjs-editor-add-signature-draw-button = Dessiner
    .title = Dessiner
pdfjs-editor-add-signature-image-button = Image
    .title = Image

## Tab panels

pdfjs-editor-add-signature-type-input =
    .aria-label = Saisissez votre signature
    .placeholder = Saisissez votre signature
pdfjs-editor-add-signature-draw-placeholder = Tracez votre signature
pdfjs-editor-add-signature-draw-thickness-range-label = Épaisseur
# Variables:
#   $thickness (Number) - the thickness (in pixels) of the line used to draw a signature.
pdfjs-editor-add-signature-draw-thickness-range =
    .title = Épaisseur du trait : { $thickness }
pdfjs-editor-add-signature-image-placeholder = Déposez un fichier ici pour l’envoyer
pdfjs-editor-add-signature-image-browse-link =
    { PLATFORM() ->
        [macos] Ou choisissez parmi les fichiers image
       *[other] Ou parcourez les fichiers image
    }

## Controls

pdfjs-editor-add-signature-description-label = Description (texte alternatif)
pdfjs-editor-add-signature-description-input =
    .title = Description (texte alternatif)
pdfjs-editor-add-signature-description-default-when-drawing = Signature
pdfjs-editor-add-signature-clear-button-label = Effacer la signature
pdfjs-editor-add-signature-clear-button =
    .title = Effacer la signature
pdfjs-editor-add-signature-save-checkbox = Enregistrer la signature
pdfjs-editor-add-signature-save-warning-message = Vous avez atteint la limite de 5 signatures enregistrées. Supprimez-en une pour en enregistrer une autre.
pdfjs-editor-add-signature-image-upload-error-title = Impossible d’envoyer l’image
pdfjs-editor-add-signature-image-upload-error-description = Vérifiez votre connexion réseau ou essayez avec une autre image.
pdfjs-editor-add-signature-image-no-data-error-title = Impossible de convertir cette image en signature
pdfjs-editor-add-signature-image-no-data-error-description = Veuillez essayer d’envoyer une autre image.
pdfjs-editor-add-signature-error-close-button = Fermer

## Dialog buttons

pdfjs-editor-add-signature-cancel-button = Annuler
pdfjs-editor-add-signature-add-button = Ajouter
pdfjs-editor-edit-signature-update-button = Mettre à jour

## Comment popup

pdfjs-editor-edit-comment-popup-button-label = Modifier le commentaire
pdfjs-editor-edit-comment-popup-button =
    .title = Modifier le commentaire
pdfjs-editor-delete-comment-popup-button-label = Supprimer le commentaire
pdfjs-editor-delete-comment-popup-button =
    .title = Supprimer le commentaire
pdfjs-show-comment-button =
    .title = Voir les commentaires

##  Edit a comment dialog

# An existing comment is edited
pdfjs-editor-edit-comment-dialog-title-when-editing = Modifier le commentaire
pdfjs-editor-edit-comment-dialog-save-button-when-editing = Mettre à jour
# No existing comment
pdfjs-editor-edit-comment-dialog-title-when-adding = Ajouter un commentaire
pdfjs-editor-edit-comment-dialog-save-button-when-adding = Ajouter
pdfjs-editor-edit-comment-dialog-text-input =
    .placeholder = Commencer à écrire…
pdfjs-editor-edit-comment-dialog-cancel-button = Annuler

## Edit a comment button in the editor toolbar

pdfjs-editor-add-comment-button =
    .title = Ajouter un commentaire

## The view manager is a sidebar displaying different views:
##  - thumbnails;
##  - outline;
##  - attachments;
##  - layers.
## The thumbnails view is used to edit the pdf: remove/insert pages, ...

pdfjs-toggle-views-manager-notification-button =
    .title = Afficher/Masquer le panneau latéral (le document contient des vignettes/plan/pièces jointes/calques)
pdfjs-toggle-views-manager-button1-label = Gérer les pages
pdfjs-views-manager-sidebar =
    .aria-label = Panneau latéral
pdfjs-views-manager-sidebar-resizer =
    .aria-label = Redimensionner le panneau latéral
pdfjs-views-manager-view-selector-button =
    .title = Vues
pdfjs-views-manager-view-selector-button-label = Vues
pdfjs-views-manager-pages-title = Pages
pdfjs-views-manager-outlines-title1 = Structure du document
    .title = Structure du document (double-cliquer pour développer/réduire tous les éléments)
pdfjs-views-manager-attachments-title = Pièces jointes
pdfjs-views-manager-layers-title1 = Calques
    .title = Calques (double-cliquer pour réinitialiser tous les calques à leur état par défaut)
pdfjs-views-manager-pages-option-label = Pages
pdfjs-views-manager-outlines-option-label = Signets du document
pdfjs-views-manager-attachments-option-label = Pièces jointes
pdfjs-views-manager-layers-option-label = Calques
pdfjs-views-manager-add-file-button =
    .title = Ajouter un fichier
pdfjs-views-manager-add-file-button-label = Ajouter un fichier
# Variables:
#   $count (Number) - the number of selected pages.
pdfjs-views-manager-pages-status-action-label =
    { $count ->
        [one] { $count } page sélectionnée
       *[other] { $count } pages sélectionnées
    }
pdfjs-views-manager-pages-status-none-action-label = Sélectionner des pages
pdfjs-views-manager-pages-status-action-button-label = Gérer
pdfjs-views-manager-pages-status-copy-button-label = Copier
pdfjs-views-manager-pages-status-cut-button-label = Couper
pdfjs-views-manager-pages-status-delete-button-label = Supprimer
pdfjs-views-manager-pages-status-export-selected-button-label = Exporter la sélection…
# Variables:
#   $count (Number) - the number of selected pages to be cut.
pdfjs-views-manager-status-undo-cut-label =
    { $count ->
        [one] 1 page coupée
       *[other] { $count } pages coupées
    }
# Variables:
#   $count (Number) - the number of selected pages to be copied.
pdfjs-views-manager-pages-status-undo-copy-label =
    { $count ->
        [one] 1 page copiée
       *[other] { $count } pages copiées
    }
# Variables:
#   $count (Number) - the number of selected pages to be deleted.
pdfjs-views-manager-pages-status-undo-delete-label =
    { $count ->
        [one] 1 page supprimée
       *[other] { $count } pages supprimées
    }
pdfjs-views-manager-pages-status-waiting-ready-label = Préparation de votre fichier…
pdfjs-views-manager-pages-status-waiting-uploading-label = Envoi du fichier…
pdfjs-views-manager-status-warning-cut-label = Impossible de couper. Actualisez la page et essayez à nouveau.
pdfjs-views-manager-status-warning-copy-label = Copie impossible. Actualisez la page et essayez à nouveau.
pdfjs-views-manager-status-warning-delete-label = Suppression impossible. Actualisez la page et essayez à nouveau.
pdfjs-views-manager-status-warning-save-label = Enregistrement impossible. Actualisez la page et essayez à nouveau.
pdfjs-views-manager-status-undo-button-label = Annuler
pdfjs-views-manager-status-done-button-label = Terminer
pdfjs-views-manager-status-close-button =
    .title = Fermer
pdfjs-views-manager-status-close-button-label = Fermer
pdfjs-views-manager-paste-button-label = Coller
pdfjs-views-manager-paste-button-before =
    .title = Coller avant la première page
# Variables:
#   $page (Number) - the page number after which the paste button is.
pdfjs-views-manager-paste-button-after =
    .title = Coller après la page { $page }
# Badge used to promote a new feature in the UI, keep it as short as possible.
# It's spelled uppercase for English, but it can be translated as usual.
pdfjs-new-badge-content = NOUVEAU
pdfjs-views-manager-waiting-for-file = Envoi du fichier…
pdfjs-toggle-views-manager-button1 =
    .title = Gérer les pages

## Digital signature properties (signature verification panel)

pdfjs-digital-signature-properties-button =
    .aria-label = Propriétés de la signature numérique
    .title = Propriétés de la signature numérique
pdfjs-digital-signature-properties-button-label = Propriétés de la signature numérique

## Banner shown above the signature list summarising the overall
## verification state of the document. Each variant is selected by the
## viewer based on the worst per-signature status; one signature is
## enough to lower the banner.
##
## Variables:
##   $count (Number) - number of signatures at the worst level.

pdfjs-digital-signature-properties-banner-verified = Le document a été signé avec une signature numérique valide
pdfjs-digital-signature-properties-banner-unknown =
    { $count ->
        [one] Document signé mais { $count } signature numérique n’a pas pu être vérifiée
       *[other] Document signé mais { $count } signatures numériques n’ont pas pu être vérifiées
    }
pdfjs-digital-signature-properties-banner-untrusted =
    { $count ->
        [1] Document signé avec un certificat non digne de confiance
       *[other] Document signé avec { $count } certificats non dignes de confiance
    }
pdfjs-digital-signature-properties-banner-expired =
    { $count ->
        [1] Document signé avec un certificat expiré
       *[other] Document signé avec { $count } certificats expirés
    }
pdfjs-digital-signature-properties-banner-invalid =
    { $count ->
        [1] Le document contient une signature numérique non valide
       *[other] Le document contient { $count } signatures numériques non valides
    }
pdfjs-digital-signature-properties-banner-revoked =
    { $count ->
        [1] Document signé avec un certificat révoqué
       *[other] Document signé avec { $count } certificats révoqués
    }

## Per-signature status row. Only three distinct strings are needed:
## the signature crypto either verified (the cert chain may still be
## untrusted/expired/revoked, but that's surfaced on the cert row
## below), or it failed, or its sub-format isn't supported.

pdfjs-digital-signature-properties-status-verified = État : signature vérifiée
pdfjs-digital-signature-properties-status-invalid = État : signature invalide
pdfjs-digital-signature-properties-status-unknown = État : impossible à vérifier (non pris en charge)

## Per-signature certificate row. The variants with an issuer / date in
## parentheses embed fully-localized context — no English fall-through.
##
## Variables:
##   $issuer (String) - issuer or subject common name from the cert.
##   $dateObj (Date)  - notAfter date for the expired-with-date form.

pdfjs-digital-signature-properties-certificate-trusted = Certificat : fiable ({ $issuer })
pdfjs-digital-signature-properties-certificate-unknown = Certificat : indisponible
pdfjs-digital-signature-properties-certificate-untrusted = Certificat : non fiable
pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Certificat : émetteur inconnu ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-self-signed = Certificat : auto-signé ({ $issuer })
pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Certificat : émetteur non fiable ({ $issuer })
pdfjs-digital-signature-properties-certificate-expired = Certificat : expiré
pdfjs-digital-signature-properties-certificate-expired-with-date = Certificat : expiré ({ DATETIME($dateObj, dateStyle: "medium") })
pdfjs-digital-signature-properties-certificate-revoked = Certificat : révoqué

## Main menu for adding/removing signatures

pdfjs-editor-delete-signature-button1 =
    .title = Supprimer la signature enregistrée
pdfjs-editor-delete-signature-button-label1 = Supprimer la signature enregistrée

## Editor toolbar

pdfjs-editor-add-signature-edit-button-label = Modifier la description

## Edit signature description dialog

pdfjs-editor-edit-signature-dialog-title = Modifier la description
