from odoo import http
from odoo.http import request


EFFECTIVE_DATE = "March 14, 2026"
SERVICE_NAME = "Kodoo"
SERVICE_DOMAIN = "kodoo.online"
OPERATOR_NAME = "Kodoo for MD Portfolio companies and invited affiliates"
LEGAL_CONTACT_EMAIL = "legal@kodoo.online"
PRIVACY_CONTACT_EMAIL = "privacy@kodoo.online"


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
