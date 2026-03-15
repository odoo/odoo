from odoo import http
from odoo.http import request


EFFECTIVE_DATE = "March 14, 2026"
SERVICE_NAME = "Kodoo"
SERVICE_DOMAIN = "kodoo.online"
OPERATOR_NAME = "Kodoo for MD Portfolio companies and invited affiliates"
LEGAL_CONTACT_EMAIL = "legal@kodoo.online"
PRIVACY_CONTACT_EMAIL = "privacy@kodoo.online"
QUICKBOOKS_BASE_PATH = "/quickbooks"


def _absolute_url(path):
    return f"https://{SERVICE_DOMAIN}{path}"


def _quickbooks_urls():
    return {
        "host_domain": SERVICE_DOMAIN,
        "hub_path": QUICKBOOKS_BASE_PATH,
        "hub_url": _absolute_url(QUICKBOOKS_BASE_PATH),
        "connect_path": f"{QUICKBOOKS_BASE_PATH}/connect",
        "connect_url": _absolute_url(f"{QUICKBOOKS_BASE_PATH}/connect"),
        "launch_path": f"{QUICKBOOKS_BASE_PATH}/launch",
        "launch_url": _absolute_url(f"{QUICKBOOKS_BASE_PATH}/launch"),
        "disconnect_path": f"{QUICKBOOKS_BASE_PATH}/disconnect",
        "disconnect_url": _absolute_url(f"{QUICKBOOKS_BASE_PATH}/disconnect"),
    }


def _privacy_policy_sections():
    return [
        {
            "heading": "1. Scope",
            "paragraphs": [
                (
                    "This Privacy Policy applies to Kodoo services made available at "
                    "kodoo.online, including dashboards, mirrored accounting views, and "
                    "analytics workflows that connect to QuickBooks Online, Odoo, and "
                    "other business systems approved by the customer."
                ),
                (
                    "If you access Kodoo through your employer, fund, portfolio company, "
                    "or another organization, that organization remains responsible for "
                    "its underlying business records and may instruct us on how the "
                    "service is configured, administered, and deactivated."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "2. Information We Collect",
            "paragraphs": [
                "We collect information needed to operate, secure, and support the service."
            ],
            "bullets": [
                (
                    "Account and organization details, such as names, work email "
                    "addresses, company names, and user roles."
                ),
                (
                    "Connection and authorization data, such as API credentials, OAuth "
                    "tokens, refresh tokens, and integration settings supplied for "
                    "QuickBooks Online or other connected services."
                ),
                (
                    "Business data that authorized users choose to sync or mirror, "
                    "including chart of accounts, transactions, vendors, customers, "
                    "invoices, bills, payments, reports, and related metadata."
                ),
                (
                    "Usage and diagnostic data, such as login events, IP addresses, "
                    "browser details, request logs, error traces, and audit events."
                ),
                (
                    "Support and operational communications, including messages sent to "
                    "our team and records needed to resolve incidents."
                ),
            ],
        },
        {
            "heading": "3. How We Use Information",
            "paragraphs": [
                "We use collected information only for legitimate business and service operations."
            ],
            "bullets": [
                "To authenticate users, maintain sessions, and manage permissions.",
                (
                    "To mirror, normalize, and display authorized accounting and "
                    "operational data inside Kodoo dashboards and reports."
                ),
                (
                    "To generate cross-company or portfolio-level analysis when that "
                    "view has been expressly enabled by the customer organization."
                ),
                "To monitor performance, troubleshoot incidents, and improve reliability.",
                "To detect abuse, fraud, or unauthorized access attempts.",
                "To comply with legal obligations, enforce contracts, and maintain records.",
            ],
        },
        {
            "heading": "4. QuickBooks And Connected-Service Data",
            "paragraphs": [
                (
                    "When you connect QuickBooks Online or another third-party service, "
                    "you authorize Kodoo to access only the data and scopes granted by "
                    "that connection. We use connected-service data solely to provide "
                    "the syncing, dashboarding, reporting, and analysis features "
                    "requested by the customer."
                ),
                (
                    "We do not sell QuickBooks-connected data, do not use it for "
                    "third-party advertising, and do not disclose it to unrelated "
                    "parties except as necessary to host, secure, or support the "
                    "service, or where disclosure is required by law."
                ),
                (
                    "If an authorized customer disconnects an integration or requests "
                    "deletion, we will disable further access and handle cached data, "
                    "tokens, and derived records in accordance with our retention and "
                    "deletion procedures, typically within 30 days unless a longer "
                    "period is required for security, backup, audit, dispute, or legal reasons."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "5. Sharing And Disclosure",
            "paragraphs": [
                "We share information only in limited circumstances."
            ],
            "bullets": [
                (
                    "With infrastructure, hosting, monitoring, backup, and support "
                    "providers that process data on our behalf under confidentiality obligations."
                ),
                (
                    "With affiliated companies, administrators, or delegated operators "
                    "within the same customer group when the organization has enabled a "
                    "shared or portfolio-wide reporting setup."
                ),
                (
                    "With professional advisers or competent authorities when required "
                    "to comply with law, protect rights, investigate misuse, or respond "
                    "to lawful requests."
                ),
                (
                    "In connection with a merger, restructuring, financing, or sale of "
                    "the service, subject to appropriate confidentiality protections."
                ),
            ],
        },
        {
            "heading": "6. Retention",
            "paragraphs": [
                (
                    "We keep personal and business data only for as long as needed to "
                    "provide the service, maintain security logs, support legitimate "
                    "backup and audit cycles, resolve disputes, and meet legal or "
                    "contractual obligations."
                ),
                (
                    "Retention periods may differ by data type, customer contract, and "
                    "regulatory requirement. When information is no longer required, we "
                    "delete it, anonymize it, or isolate it from active use."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "7. Security",
            "paragraphs": [
                (
                    "We use reasonable administrative, technical, and organizational "
                    "measures designed to protect information against unauthorized "
                    "access, misuse, alteration, and loss. These measures may include "
                    "access controls, credential management, logging, environment "
                    "segregation, and secure deployment practices."
                ),
                (
                    "No system is perfectly secure. Customers are responsible for "
                    "protecting their own devices, credentials, and administrator accounts."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "8. International Transfers",
            "paragraphs": [
                (
                    "Kodoo and its service providers may process information in more "
                    "than one country. By using the service, the customer authorizes "
                    "transfers that are reasonably necessary to host, secure, and "
                    "support the platform, subject to applicable law and contractual safeguards."
                )
            ],
            "bullets": [],
        },
        {
            "heading": "9. Rights And Choices",
            "paragraphs": [
                (
                    "Depending on applicable law, you or your organization may have "
                    "rights to access, correct, export, restrict, or delete certain "
                    "personal information. Because Kodoo is primarily a business-facing "
                    "service, many requests should first be directed to the organization "
                    "that controls the account."
                ),
                (
                    "To request privacy assistance or report a concern, contact "
                    "privacy@kodoo.online."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "10. Changes To This Policy",
            "paragraphs": [
                (
                    "We may update this Privacy Policy from time to time. Material "
                    "changes will be reflected by updating the effective date on this page."
                )
            ],
            "bullets": [],
        },
    ]


def _eula_sections():
    return [
        {
            "heading": "1. Acceptance And Eligibility",
            "paragraphs": [
                (
                    "This End-User License Agreement applies to your access to Kodoo at "
                    "kodoo.online and to any dashboards, mirrored accounting views, "
                    "analytics outputs, and integration features made available through the service."
                ),
                (
                    "You may use Kodoo only on behalf of yourself or the organization "
                    "that authorized your account. By using the service, you confirm "
                    "that you have authority to accept these terms for that user or organization."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "2. License Grant",
            "paragraphs": [
                (
                    "Subject to these terms, Kodoo grants you a limited, revocable, "
                    "non-exclusive, non-transferable license to access and use the "
                    "service for internal business purposes."
                )
            ],
            "bullets": [
                "The license is limited to the features, users, entities, and data sources approved for your account.",
                "No ownership rights are transferred to you except for your own customer data.",
            ],
        },
        {
            "heading": "3. Customer Data And Ownership",
            "paragraphs": [
                (
                    "The customer retains ownership of its accounting, operational, "
                    "and business data. Kodoo may host, cache, transform, and display "
                    "that data solely to provide the contracted service."
                ),
                (
                    "If your organization enables portfolio-wide reporting across "
                    "multiple companies, you are responsible for ensuring that the "
                    "participating entities and users are authorized to share that visibility."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "4. Connected Services",
            "paragraphs": [
                (
                    "Kodoo may connect to QuickBooks Online, Odoo, banks, or other "
                    "third-party systems selected by the customer. Your use of those "
                    "connections is also subject to the terms and policies of the "
                    "underlying third-party providers."
                ),
                (
                    "You are responsible for ensuring that credentials, tokens, and "
                    "permissions supplied to Kodoo are accurate and authorized. You "
                    "must promptly revoke access that is no longer required."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "5. Acceptable Use",
            "paragraphs": [
                "You agree not to misuse the service."
            ],
            "bullets": [
                "Do not attempt to bypass authentication, authorization, rate limits, or security controls.",
                "Do not upload malicious code, unlawful content, or data you are not authorized to process.",
                "Do not copy, reverse engineer, scrape, or resell the service except as allowed by law or written agreement.",
                "Do not use Kodoo in a way that could impair service availability for other users.",
            ],
        },
        {
            "heading": "6. Confidentiality And Security",
            "paragraphs": [
                (
                    "You must keep account credentials confidential and use reasonable "
                    "security measures to protect devices, browsers, API secrets, and "
                    "administrator access under your control."
                ),
                (
                    "You must notify Kodoo promptly if you suspect unauthorized access, "
                    "credential compromise, or accidental disclosure of protected data."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "7. Service Changes, Support, And Beta Features",
            "paragraphs": [
                (
                    "Kodoo may update, improve, suspend, or retire features from time "
                    "to time. Some functions may rely on third-party APIs, data "
                    "availability, or beta capabilities that can change without notice."
                ),
                (
                    "We will use commercially reasonable efforts to maintain service "
                    "availability, but uninterrupted operation is not guaranteed."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "8. Intellectual Property",
            "paragraphs": [
                (
                    "Kodoo and its related software, branding, layouts, workflows, and "
                    "documentation remain the property of their respective owners. "
                    "Feedback may be used to improve the service without restriction or compensation."
                )
            ],
            "bullets": [],
        },
        {
            "heading": "9. Suspension And Termination",
            "paragraphs": [
                (
                    "We may suspend or terminate access if required for security, "
                    "non-payment, legal compliance, misuse, or a material breach of these terms."
                ),
                (
                    "You may stop using the service at any time. Upon termination, your "
                    "right to access the service ends, but sections that reasonably "
                    "should survive termination remain in effect."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "10. Disclaimers",
            "paragraphs": [
                (
                    "Except as expressly agreed in writing, Kodoo is provided on an "
                    "\"as is\" and \"as available\" basis. Reports, dashboards, and "
                    "mirrored data are operational tools and do not replace independent "
                    "finance, tax, legal, or audit review."
                )
            ],
            "bullets": [],
        },
        {
            "heading": "11. Limitation Of Liability",
            "paragraphs": [
                (
                    "To the maximum extent permitted by law, Kodoo will not be liable "
                    "for indirect, incidental, special, consequential, exemplary, or "
                    "punitive damages, or for loss of profits, revenue, goodwill, or data."
                ),
                (
                    "If liability cannot be excluded, Kodoo's aggregate liability for "
                    "claims arising out of the service will be limited to the amounts "
                    "paid for the affected service during the twelve months before the claim arose."
                ),
            ],
            "bullets": [],
        },
        {
            "heading": "12. General Terms",
            "paragraphs": [
                (
                    "These terms may be supplemented by a signed services agreement, "
                    "statement of work, or organization-specific order form. If there "
                    "is a conflict, the signed agreement controls for that customer."
                ),
                (
                    "Questions about this EULA may be sent to legal@kodoo.online."
                ),
            ],
            "bullets": [],
        },
    ]


class KodooLegalController(http.Controller):
    def _base_values(self, page_key, page_title, summary, meta_description, sections):
        return {
            "page_key": page_key,
            "page_title": page_title,
            "summary": summary,
            "meta_description": meta_description,
            "sections": sections,
            "effective_date": EFFECTIVE_DATE,
            "service_name": SERVICE_NAME,
            "service_domain": SERVICE_DOMAIN,
            "operator_name": OPERATOR_NAME,
            "legal_contact_email": LEGAL_CONTACT_EMAIL,
            "privacy_contact_email": PRIVACY_CONTACT_EMAIL,
            "current_path": request.httprequest.path,
        }

    def _integration_values(
        self,
        page_key,
        page_title,
        summary,
        notice,
        cards,
        sections,
        primary_action=None,
        secondary_action=None,
    ):
        urls = _quickbooks_urls()
        normalized_cards = []
        for card in cards:
            normalized_cards.append(
                {
                    "label": card["label"],
                    "value": card["value"],
                    "description": card["description"],
                    "href": card.get("href", ""),
                    "action_label": card.get("action_label", ""),
                }
            )
        return {
            "page_key": page_key,
            "page_title": page_title,
            "summary": summary,
            "meta_description": summary,
            "notice": notice,
            "cards": normalized_cards,
            "sections": sections,
            "primary_action": primary_action,
            "secondary_action": secondary_action,
            "effective_date": EFFECTIVE_DATE,
            "service_name": SERVICE_NAME,
            "service_domain": SERVICE_DOMAIN,
            "operator_name": OPERATOR_NAME,
            "legal_contact_email": LEGAL_CONTACT_EMAIL,
            "privacy_contact_email": PRIVACY_CONTACT_EMAIL,
            "urls": urls,
            "current_path": request.httprequest.path,
        }

    @http.route(
        [
            "/privacy-policy",
            "/privacy-policy/",
            "/privacy",
            "/privacy/",
            "/legal/privacy-policy",
            "/legal/privacy-policy/",
        ],
        type="http",
        auth="public",
        methods=["GET"],
    )
    def privacy_policy(self, **kwargs):
        del kwargs
        summary = (
            "How Kodoo collects, uses, stores, and discloses information while "
            "powering QuickBooks-connected mirrors, dashboards, and analytics workflows."
        )
        return request.render(
            "kodoo_legal.document_page",
            self._base_values(
                page_key="privacy_policy",
                page_title="Privacy Policy",
                summary=summary,
                meta_description=summary,
                sections=_privacy_policy_sections(),
            ),
        )

    @http.route(
        [
            "/eula",
            "/eula/",
            "/end-user-license-agreement",
            "/end-user-license-agreement/",
            "/terms",
            "/terms/",
            "/terms-of-service",
            "/terms-of-service/",
        ],
        type="http",
        auth="public",
        methods=["GET"],
    )
    def eula(self, **kwargs):
        del kwargs
        summary = (
            "The terms that govern use of Kodoo, including mirrored QuickBooks data, "
            "dashboards, integrations, and multi-company portfolio reporting."
        )
        return request.render(
            "kodoo_legal.document_page",
            self._base_values(
                page_key="eula",
                page_title="End-User License Agreement",
                summary=summary,
                meta_description=summary,
                sections=_eula_sections(),
            ),
        )

    @http.route(
        ["/quickbooks", "/quickbooks/", "/qbo", "/qbo/"],
        type="http",
        auth="public",
        methods=["GET"],
    )
    def quickbooks_hub(self, **kwargs):
        del kwargs
        urls = _quickbooks_urls()
        cards = [
            {
                "label": "Host domain",
                "value": urls["host_domain"],
                "description": "Enter this customer-facing domain in QuickBooks without the https protocol.",
            },
            {
                "label": "Launch URL",
                "value": urls["launch_url"],
                "description": "Send customers here after authentication so they can continue into Kodoo.",
                "href": urls["launch_path"],
                "action_label": "Open launch page",
            },
            {
                "label": "Disconnect URL",
                "value": urls["disconnect_url"],
                "description": "Use this public page to guide customers through disconnect and data-removal requests.",
                "href": urls["disconnect_path"],
                "action_label": "Open disconnect page",
            },
            {
                "label": "Connect/Reconnect URL",
                "value": urls["connect_url"],
                "description": "Use this page as the customer-facing entry point for first-time connection and reconnection.",
                "href": urls["connect_path"],
                "action_label": "Open connect page",
            },
        ]
        sections = [
            {
                "heading": "How To Use These URLs",
                "paragraphs": [
                    (
                        "These URLs are public, customer-facing pages served directly "
                        "from the Odoo-backed kodoo.online domain so they remain stable "
                        "for Intuit app review, onboarding, and support."
                    ),
                    (
                        "The connect page is the front door for initial setup and "
                        "reconnection. The launch page is the post-authentication "
                        "destination. The disconnect page documents how customers can "
                        "end access and request removal of synchronized data."
                    ),
                ],
                "bullets": [
                    "Keep the host domain as kodoo.online with no protocol.",
                    "Use the https URLs exactly as published below.",
                    "Pair these routes with the public Privacy Policy and EULA pages already in this module.",
                ],
            }
        ]
        return request.render(
            "kodoo_legal.integration_page",
            self._integration_values(
                page_key="quickbooks_hub",
                page_title="QuickBooks App Setup Hub",
                summary=(
                    "Customer-facing setup pages and canonical URLs for the Kodoo "
                    "QuickBooks-connected dashboard and mirror experience."
                ),
                notice=(
                    "Use this hub as the operational reference for app-review fields, "
                    "support handoff, and customer onboarding."
                ),
                cards=cards,
                sections=sections,
                primary_action={"label": "Open Connect Page", "href": urls["connect_path"]},
                secondary_action={"label": "Review Privacy Policy", "href": "/privacy-policy"},
            ),
        )

    @http.route(
        [
            "/quickbooks/connect",
            "/quickbooks/connect/",
            "/quickbooks/reconnect",
            "/quickbooks/reconnect/",
            "/qbo/connect",
            "/qbo/connect/",
        ],
        type="http",
        auth="public",
        methods=["GET"],
    )
    def quickbooks_connect(self, **kwargs):
        del kwargs
        urls = _quickbooks_urls()
        cards = [
            {
                "label": "Canonical connect URL",
                "value": urls["connect_url"],
                "description": "Use this exact https URL in QuickBooks for both connect and reconnect actions.",
            },
            {
                "label": "Next destination",
                "value": urls["launch_url"],
                "description": "After sign-in or authorization, customers should continue to the launch page.",
                "href": urls["launch_path"],
                "action_label": "Preview launch page",
            },
        ]
        sections = [
            {
                "heading": "Connection Flow",
                "paragraphs": [
                    (
                        "Customers should begin here when linking QuickBooks Online to "
                        "Kodoo for the first time or when refreshing a previously revoked connection."
                    ),
                    (
                        "This page can later hand off directly to the production OAuth "
                        "flow without changing the public URL, which keeps your app-review metadata stable."
                    ),
                ],
                "bullets": [
                    "Authenticate to Kodoo with an authorized company account.",
                    "Approve QuickBooks scopes only for the entities you want mirrored into Kodoo.",
                    "Return to the launch page to continue into dashboards and reporting.",
                ],
            }
        ]
        return request.render(
            "kodoo_legal.integration_page",
            self._integration_values(
                page_key="quickbooks_connect",
                page_title="Connect Or Reconnect QuickBooks",
                summary=(
                    "Start or refresh a QuickBooks connection for Kodoo's mirrored "
                    "dashboards, portfolio reporting, and analytics workflows."
                ),
                notice=(
                    "If you are not sure which company file or administrator account to "
                    "use, pause here and confirm the correct QuickBooks entity before connecting."
                ),
                cards=cards,
                sections=sections,
                primary_action={
                    "label": "Sign In To Kodoo",
                    "href": f"/web/login?redirect={urls['launch_path']}",
                },
                secondary_action={"label": "Open Setup Hub", "href": urls["hub_path"]},
            ),
        )

    @http.route(
        ["/quickbooks/launch", "/quickbooks/launch/", "/qbo/launch", "/qbo/launch/"],
        type="http",
        auth="public",
        methods=["GET"],
    )
    def quickbooks_launch(self, **kwargs):
        del kwargs
        urls = _quickbooks_urls()
        cards = [
            {
                "label": "Canonical launch URL",
                "value": urls["launch_url"],
                "description": "Use this exact https URL as the post-authentication destination in QuickBooks setup.",
            },
            {
                "label": "Workspace entry",
                "value": _absolute_url("/web"),
                "description": "After authentication, continue into the Kodoo workspace and dashboards.",
                "href": "/web",
                "action_label": "Open Kodoo workspace",
            },
        ]
        sections = [
            {
                "heading": "After Authentication",
                "paragraphs": [
                    (
                        "Customers arrive here after authenticating or finishing an "
                        "integration handoff. From here they can continue into the Kodoo "
                        "workspace, dashboards, and company-level reporting."
                    ),
                    (
                        "If the QuickBooks connection still requires a final approval step, "
                        "an administrator can complete it from the Kodoo workspace without changing this URL."
                    ),
                ],
                "bullets": [
                    "Open the Kodoo workspace.",
                    "Confirm the intended company or portfolio scope.",
                    "Review the Privacy Policy and EULA before enabling live synchronization.",
                ],
            }
        ]
        return request.render(
            "kodoo_legal.integration_page",
            self._integration_values(
                page_key="quickbooks_launch",
                page_title="Launch Kodoo After Authentication",
                summary=(
                    "Post-authentication landing page for customers continuing from "
                    "QuickBooks into Kodoo."
                ),
                notice=(
                    "This route is safe to publish in review forms because it stays "
                    "customer-facing even before the full OAuth callback flow is finalized."
                ),
                cards=cards,
                sections=sections,
                primary_action={"label": "Open Kodoo Workspace", "href": "/web"},
                secondary_action={"label": "Review EULA", "href": "/eula"},
            ),
        )

    @http.route(
        [
            "/quickbooks/disconnect",
            "/quickbooks/disconnect/",
            "/qbo/disconnect",
            "/qbo/disconnect/",
        ],
        type="http",
        auth="public",
        methods=["GET"],
    )
    def quickbooks_disconnect(self, **kwargs):
        del kwargs
        urls = _quickbooks_urls()
        cards = [
            {
                "label": "Canonical disconnect URL",
                "value": urls["disconnect_url"],
                "description": "Use this exact https URL in QuickBooks setup for customer-facing disconnect guidance.",
            },
            {
                "label": "Privacy contact",
                "value": PRIVACY_CONTACT_EMAIL,
                "description": "Use this contact for integration removal and cached-data deletion requests.",
                "href": f"mailto:{PRIVACY_CONTACT_EMAIL}",
                "action_label": "Email privacy team",
            },
        ]
        sections = [
            {
                "heading": "Disconnecting The App",
                "paragraphs": [
                    (
                        "If you want to stop sharing QuickBooks data with Kodoo, begin "
                        "by notifying your Kodoo administrator or portfolio operator so "
                        "they can identify the exact company and connection to revoke."
                    ),
                    (
                        "Disconnecting access may stop future synchronization before all "
                        "cached or derived data is removed. Requests involving deletion "
                        "or retention are handled under the Privacy Policy and the "
                        "customer's contractual data-management obligations."
                    ),
                ],
                "bullets": [
                    "Ask an authorized administrator to revoke or rotate the active integration credentials.",
                    "Email privacy@kodoo.online if you need deletion or disconnect confirmation.",
                    "Review the Privacy Policy for retention and data-removal handling.",
                ],
            }
        ]
        return request.render(
            "kodoo_legal.integration_page",
            self._integration_values(
                page_key="quickbooks_disconnect",
                page_title="Disconnect QuickBooks From Kodoo",
                summary=(
                    "Customer-facing guidance for disconnecting QuickBooks access and "
                    "requesting handling of synchronized data."
                ),
                notice=(
                    "This page is intentionally public so customers and reviewers can see "
                    "a stable disconnect destination even before self-service revocation is automated."
                ),
                cards=cards,
                sections=sections,
                primary_action={
                    "label": "Email Privacy Team",
                    "href": f"mailto:{PRIVACY_CONTACT_EMAIL}",
                },
                secondary_action={"label": "Review Privacy Policy", "href": "/privacy-policy"},
            ),
        )
