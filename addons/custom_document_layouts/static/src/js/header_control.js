odoo.define('custom_document_layouts.header_control', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');

    var HeaderControl = publicWidget.Widget.extend({
        selector: 'body',

        start: function () {
            var self = this;
            this._super.apply(this, arguments);

            // Attendre que le DOM soit complètement chargé
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function () {
                    self._controlHeaderDisplay();
                });
            } else {
                this._controlHeaderDisplay();
            }

            // Observer les changements dans le document pour les PDF générés dynamiquement
            this._observePageChanges();
        },

        _controlHeaderDisplay: function () {
            var self = this;

            // Détecter si on est en mode PDF
            if (this._isPDFMode()) {
                console.log('Mode PDF détecté, application du contrôle header...');

                // Attendre un peu que le PDF soit généré
                setTimeout(function () {
                    self._hideHeaderOnNonFirstPages();
                }, 100);

                // Réessayer plusieurs fois au cas où
                setTimeout(function () {
                    self._hideHeaderOnNonFirstPages();
                }, 500);

                setTimeout(function () {
                    self._hideHeaderOnNonFirstPages();
                }, 1000);
            }
        },

        _isPDFMode: function () {
            // Vérifier différents indicateurs de mode PDF
            return document.querySelector('[data-report-type="pdf"]') ||
                window.location.href.indexOf('/report/pdf/') !== -1 ||
                window.location.href.indexOf('report_type=pdf') !== -1 ||
                document.body.classList.contains('o_report_layout_standard');
        },

        _hideHeaderOnNonFirstPages: function () {
            console.log('Recherche des headers à masquer...');

            // Méthode 1: Cibler les headers par classes spécifiques
            var headers = document.querySelectorAll('.header, [class*="o_company_"], .container.mt-3');

            headers.forEach(function (header, index) {
                // Vérifier si ce header contient les infos de facture (indicateur du header principal)
                var hasInvoiceInfo = header.querySelector('table') &&
                    (header.textContent.indexOf('Document N°') !== -1 ||
                        header.textContent.indexOf('FACTURE') !== -1);

                if (hasInvoiceInfo) {
                    // Marquer le premier header comme étant sur la première page
                    if (index === 0) {
                        header.setAttribute('data-first-page-header', 'true');
                        header.style.display = 'block';
                        console.log('Header principal trouvé et conservé sur la première page');
                    } else {
                        // Masquer les headers suivants
                        header.style.display = 'none !important';
                        header.style.visibility = 'hidden';
                        header.style.position = 'absolute';
                        header.style.left = '-9999px';
                        header.style.top = '-9999px';
                        console.log('Header supplémentaire masqué');
                    }
                }
            });

            // Méthode 2: Injection de CSS dynamique pour être sûr
            this._injectHeaderCSS();

            // Méthode 3: Observer spécifiquement les pages
            this._observePages();
        },

        _injectHeaderCSS: function () {
            var style = document.createElement('style');
            style.type = 'text/css';
            style.id = 'header-control-css';

            // Éviter de dupliquer le style
            if (document.getElementById('header-control-css')) {
                return;
            }

            var css = `
                /* Masquer les headers sur les pages 2+ */
                @media print {
                    /* Cibler spécifiquement les pages suivantes */
                    body > div:nth-of-type(n+2) .header,
                    body > div:nth-of-type(n+2) [class*="o_company_"],
                    body > div:nth-of-type(n+2) .container.mt-3:has(table) {
                        display: none !important;
                        visibility: hidden !important;
                        position: absolute !important;
                        left: -10000px !important;
                        top: -10000px !important;
                        height: 0 !important;
                        overflow: hidden !important;
                    }
                    
                    /* Méthode alternative avec sélecteurs de pages */
                    @page ~ @page .header,
                    @page ~ @page [class*="o_company_"] {
                        display: none !important;
                    }
                    
                    /* Cibler les divs article qui ne sont pas le premier */
                    .article:not(:first-of-type) .header,
                    .article:not(:first-of-type) .container.mt-3:has(table) {
                        display: none !important;
                        visibility: hidden !important;
                    }
                }
                
                /* Pour l'aperçu web aussi */
                .page:not(.page:first-child) .header,
                .page:not(.page:first-child) .container.mt-3:has(table),
                div[data-page-number]:not([data-page-number="1"]) .header {
                    display: none !important;
                    visibility: hidden !important;
                }
            `;

            style.innerHTML = css;
            document.head.appendChild(style);
            console.log('CSS de contrôle des headers injecté');
        },

        _observePages: function () {
            var self = this;

            // Marquer les pages avec des attributs data
            var articles = document.querySelectorAll('.article, div[class*="article"]');
            articles.forEach(function (article, index) {
                article.setAttribute('data-page-number', index + 1);

                // Sur les pages 2+, masquer tous les headers
                if (index > 0) {
                    var headersInPage = article.querySelectorAll('.header, .container.mt-3:has(table), [class*="o_company_"]');
                    headersInPage.forEach(function (header) {
                        header.style.display = 'none';
                        header.style.visibility = 'hidden';
                        header.style.position = 'absolute';
                        header.style.left = '-9999px';
                    });
                }
            });
        },

        _observePageChanges: function () {
            var self = this;

            // Observer les mutations du DOM pour les changements dynamiques
            var observer = new MutationObserver(function (mutations) {
                mutations.forEach(function (mutation) {
                    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                        // Vérifier si de nouveaux éléments de page ont été ajoutés
                        var hasNewPages = false;
                        mutation.addedNodes.forEach(function (node) {
                            if (node.nodeType === Node.ELEMENT_NODE &&
                                (node.classList.contains('article') || node.querySelector && node.querySelector('.article'))) {
                                hasNewPages = true;
                            }
                        });

                        if (hasNewPages) {
                            setTimeout(function () {
                                self._hideHeaderOnNonFirstPages();
                            }, 100);
                        }
                    }
                });
            });

            // Observer le document body
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    });

    // Auto-initialisation quand le script est chargé
    $(document).ready(function () {
        console.log('Initialisation du contrôle des headers...');
        new HeaderControl().attachTo($('body'));

        // Fallback pour les cas où le widget ne s'attache pas
        setTimeout(function () {
            if (document.querySelector('[data-report-type="pdf"]') ||
                window.location.href.indexOf('/report/pdf/') !== -1) {

                var headers = document.querySelectorAll('.container.mt-3:has(table)');
                headers.forEach(function (header, index) {
                    if (index > 0) {
                        header.style.display = 'none';
                        console.log('Header fallback masqué');
                    }
                });
            }
        }, 2000);
    });

    return HeaderControl;
});