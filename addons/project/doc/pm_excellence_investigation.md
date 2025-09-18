# Investigation: What Constitutes Excellent Project Management?

**Date**: 2026-03-03
**Purpose**: Multi-source research synthesis for identifying gaps in Odoo's `project` module
**Sources**: See `pm_excellence_sources.md` for full bibliography with 200+ URLs
**Methodology**: Six parallel research streams, each claim tagged with evidence tier (1-5)

**Evidence Tiers Used Throughout:**
- **[T1]** Peer-reviewed, replicated, large N (e.g., Edmondson, Flyvbjerg, DORA)
- **[T2]** Peer-reviewed or rigorous with caveats (e.g., McKinsey-Oxford 5,400 projects)
- **[T3]** Industry surveys with known methodology (e.g., PMI Pulse, State of Agile)
- **[T4]** Vendor/consultant case studies (e.g., Scrum.org, SAFe case studies)
- **[T5]** Anecdotal, marketing, or unverified claims

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Nature of Project Success](#2-the-nature-of-project-success)
3. [The Human System: What Actually Predicts Outcomes](#3-the-human-system)
4. [Planning, Estimation, and the War Against Cognitive Bias](#4-planning-and-estimation)
5. [Methodologies: What the Evidence Says vs. What Vendors Sell](#5-methodologies)
6. [Metrics That Matter vs. Metrics That Deceive](#6-metrics)
7. [Governance: How Decisions Get Made (or Avoided)](#7-governance)
8. [Portfolio Management: The Organizational Layer](#8-portfolio-management)
9. [Risk Management: From Ritual to Culture](#9-risk-management)
10. [Continuous Improvement: Why Organizations Don't Learn](#10-continuous-improvement)
11. [Lessons from Catastrophic Failures](#11-lessons-from-failures)
12. [Modern Practices: What's Real and What's Hype](#12-modern-practices)
13. [Odoo Project Module: Current State Assessment](#13-odoo-current-state)
14. [Gap Analysis: Evidence-Based Priorities](#14-gap-analysis)
15. [Implementation Roadmap](#15-implementation-roadmap)

---

## 1. Executive Summary

This investigation asked a deceptively simple question: what separates excellent
project management from mediocre project management? The answer, drawn from
peer-reviewed meta-analyses, government audit reports, longitudinal studies, and
critical evaluation of industry surveys, is both simpler and harder than the
project management industry wants you to believe.

**Simpler**, because the highest-confidence findings reduce to a small set of
principles that have been replicated across decades: psychological safety enables
information flow; single-point accountability prevents diffusion of responsibility;
methodology matters far less than fit-to-context; estimation is systematically
biased and the fix is historical data, not better guessing; and organizations
chronically start more projects than they can resource.

**Harder**, because these principles cannot be purchased as certifications, installed
as software features, or mandated through process documents. They are organizational
capabilities that take years to build and are destroyed in months by the wrong
leadership. The project management industry — PMI, Scrum Alliance, Scaled Agile Inc.,
the consulting firms — has a structural incentive to sell frameworks, certifications,
and tools as solutions to what are fundamentally culture and leadership problems.

The investigation covers the following terrain:

- **What predicts project success** with high confidence: psychological safety,
  stakeholder engagement as requirements engineering, single-point accountability,
  and genuine (not ritual) risk management.

- **What the framework wars obscure**: methodology choice explains only ~40% of
  outcome variance. People, context, and organizational health explain the rest.
  PMI's own 2024 Pulse survey found that methodology does not statistically impact
  project success. The evidence for Agile's superiority over Waterfall is far weaker
  than the Agile industry claims, and the evidence against it is far weaker than
  traditionalists assert.

- **Where the real value lies**: flow metrics backed by mathematical theorems,
  portfolio-level visibility that prevents overcommitment, historical data that
  reduces estimation bias, and multi-dimensional success measurement that tracks
  whether projects actually deliver benefits — not just whether tasks were completed.

- **Where Odoo's project module falls short**: ten specific gaps, prioritized by
  evidence strength and implementation impact, with a phased roadmap.

---

## 2. The Nature of Project Success

### 2.1 The Iron Triangle Is Necessary but Radically Insufficient

For decades, project success was defined by the "Iron Triangle": on time, on budget,
on scope. This framework, formalized by Martin Barnes in the 1960s, is so deeply
embedded in organizational thinking that most PMOs still use it as their primary
success measure. **[T1]**

The problem was articulated precisely by Roger Atkinson in his 1999 landmark paper:
time and cost estimates are inherently uncertain ("two best guesses"), and quality is
genuinely measurable ("a phenomenon") but the Iron Triangle ignores it at the system
level. His argument was not that scope, time, and cost are irrelevant — they are
necessary constraints — but that they are an absurdly narrow definition of success
for an investment that typically exists to produce business value.

Consider a concrete example: a company invests $2M and 12 months to build a new
customer portal. The project delivers on time, on budget, and with all specified
features. By Iron Triangle standards, this is a success. But six months later, only
4% of customers use the portal — the rest call the support line as before. The
portal's design assumed customer behavior that does not exist. The project succeeded
on delivery metrics while failing completely on its reason for existing.

The reverse is equally common: a project runs 30% over budget and 4 months late, but
the product it delivers transforms market position, creates a new revenue stream, and
pays back its investment in 18 months. By Iron Triangle standards, this is a
"challenged" or "failed" project. By any reasonable business measure, it is a triumph.

### 2.2 The Multi-Dimensional Success Model

Shenhar and Dvir, in their study of 600+ projects, proposed a five-dimension model
that has been validated in subsequent research **[T2]**:

**Dimension 1: Project Efficiency (the Iron Triangle)**
Did we deliver on time, within budget, and within scope? This is the *necessary
minimum*, not the definition of success. It answers the question: "Did we manage the
delivery process competently?" — nothing more.

**Dimension 2: Impact on the Customer**
Are users actually using what we built? Are they satisfied? Has their behavior changed
in the intended way? Has their loyalty increased? This dimension measures whether the
project delivered *adoption*, not just *features*. It is typically measurable 3-12
months after delivery and requires deliberate follow-up that most organizations never
perform.

**Dimension 3: Impact on the Team**
Did team members grow their skills? Did they stay with the organization? Was morale
sustained or destroyed? This dimension acknowledges that a project delivered through
burnout and heroism has consumed organizational capital even if it met its deadline.
The 25-30% burnout rates documented in large program teams are not just a human cost —
they are a strategic cost through knowledge loss, reduced innovation, and recruitment
expense.

**Dimension 4: Business Results**
Did the project generate the return on investment that justified its funding? Did it
increase revenue, reduce cost, improve market share, or create competitive advantage?
This is typically measurable 12-24 months after delivery and requires connecting
project outcomes to business metrics — a connection most organizations never make
because the project team has long since dispersed.

**Dimension 5: Preparation for the Future**
Did the project create new technological capabilities, new organizational competencies,
new market positions, or new infrastructure that enables future initiatives? This is
the longest-horizon measure, relevant 2-5 years out, and is the dimension that
distinguishes truly excellent projects from merely adequate ones.

The empirical finding that makes this model important: projects that fail the Iron
Triangle often succeed on dimensions 2-5, and vice versa. This means using only Iron
Triangle metrics systematically misjudges project value — killing good projects that
are over budget and celebrating bad projects that are on time.

### 2.3 Benefits Realization Management

Benefits Realization Management (BRM) is the formalized practice of tracking whether
projects deliver their intended benefits after completion. Research published in the
International Journal of Project Management demonstrated that organizations formally
practicing BRM show significantly higher rates of strategic project success versus
those measuring only delivery metrics. **[T2]**

The practice has three components:

1. **Benefits identification at project initiation.** Before the project starts, define
   what benefits it is expected to produce, how they will be measured, and who is
   accountable for realizing them. These should be specific and quantifiable:
   "reduce customer support call volume by 30% within 6 months of launch" — not
   "improve customer experience."

2. **Benefits tracking during and after delivery.** Periodically measure whether the
   expected benefits are materializing. This requires measurement infrastructure that
   most organizations lack because they treat projects as ending at delivery rather
   than at benefit realization.

3. **Benefits accountability.** Someone — typically a business owner, not the PM —
   must be accountable for realizing the benefits after the project team disperses.
   Without this accountability, benefits tracking becomes an academic exercise.

The gap in most organizations, including Odoo's project module, is that project
success is measured at delivery and never revisited. The project is "done" when tasks
are completed. Whether the project actually mattered is never systematically assessed.

### 2.4 When "Success" Definitions Diverge

Research from the University of Western Scotland demonstrated that stakeholder
perception of success varies dramatically **[T2]**:

- A project finished on time and on budget may be viewed as a **failure** by end users
  (who found the product unusable) while being viewed as a **success** by the finance
  department (which only tracks budget adherence).
- A project that ran over budget may be viewed as a **success** by end users (who got
  exactly what they needed) while being viewed as a **failure** by the PMO (which
  tracks Iron Triangle metrics).

This divergence is not an edge case — it is the norm on non-trivial projects. The
implication for project management tools is that "success" should be a multi-
perspective concept with explicit definitions per stakeholder group, not a single
binary field.

---

## 3. The Human System: What Actually Predicts Outcomes

### 3.1 Psychological Safety: The Foundation

Amy Edmondson's 1999 research, published in the top-tier Administrative Science
Quarterly and replicated dozens of times since, established a finding that is
counterintuitive but robust **[T1]**:

Higher-performing teams report **more** errors and problems, not fewer.

The explanation is not that better teams have more problems. It is that better teams
create conditions under which problems can surface and be addressed early, when they
are cheap to fix. Worse teams suppress problems — through fear of blame, career risk,
or social pressure — until they become crises that are expensive or impossible to fix.

The mechanism is *team learning behavior*. Psychological safety — defined as "a shared
belief held by members of a team that the team is safe for interpersonal risk-taking"
— enables four specific behaviors:

1. **Speaking up about problems** before they become crises
2. **Asking for help** when stuck, rather than silently struggling
3. **Admitting mistakes** so they can be corrected, rather than hiding them
4. **Challenging the plan** when new information makes it wrong, rather than executing
   a plan everyone knows will fail

Google's Project Aristotle studied 250+ team-level variables across hundreds of Google
teams over two years. Psychological safety was the single strongest predictor of team
effectiveness, accounting for 43% of performance variance. The other four factors —
dependability, structure and clarity, meaning, and impact — were important but
*dependent on psychological safety as a foundation*. **[T2]**

A meta-analysis in Frontiers in Psychology (2020) confirmed this across 63 studies,
with moderate-to-strong effect sizes (Cohen's d ~0.4-0.6). **[T1]**

#### What This Means in Practice

The green-green-green-RED pattern — where projects report healthy status for months
and then suddenly catastrophic status when it is too late to recover — is, in
substantial part, a psychological safety failure. Project managers who report amber
or red status face scrutiny, extra reporting requirements, and implicit blame. The
rational response is to delay reporting problems until they are undeniable. By that
point, the project is in crisis.

The practical consequence for project management tools: **tools should make it easy
to surface problems early and hard to suppress them**. Automated health indicators
that detect schedule deviation, budget variance, or milestone slippage without
requiring human status reporting remove the social cost of bearing bad news. Risk
registers that are visible to stakeholders create transparency by default rather
than requiring courage.

#### How Psychological Safety Gets Built (and Destroyed)

**Building it** requires consistent behavior from leaders over time:

- Demonstrating vulnerability: "I don't know, let's figure it out together" signals
  that not-knowing is acceptable
- Responding to problems with "What do you need?" rather than "How did this happen?"
- Making retrospectives safe: no blame, focus on system improvement
- Celebrating error reporting: teams that catch problems early should be rewarded,
  not the teams that appear to have no problems (they do — they're hiding them)

**Destroying it** is much faster:

- A single punitive response to honest status reporting teaches the entire team that
  honesty is dangerous
- Public blame for mistakes, even once, teaches people to hide mistakes
- Rewarding hero culture (the person who works 80 hours to save a deadline) teaches
  the team that systemic problems are to be solved by individual sacrifice, not
  structural improvement

### 3.2 Stakeholder Engagement as Requirements Engineering

PMI's library consistently ranks stakeholder engagement as a top-3 critical success
factor. But the framing matters enormously. In most project management practice,
"stakeholder engagement" means *communication*: sending status updates, holding
steering committees, presenting at milestone reviews. This is necessary but misses
the point.

The evidence-backed framing is that stakeholder engagement is a *technical activity*
— specifically, it is **requirements engineering conducted through human interaction**.

Consider the NHS NPfIT disaster (Section 11). When clinicians resisted the national
electronic patient record system, the programme treated this as a *communications
problem* — resistance to change that could be overcome with better messaging and
training. In reality, the clinicians were providing accurate *requirements data*:
the system did not fit their workflows, could not accommodate the diversity of
clinical practice, and would degrade patient care. Their resistance was the
requirements specification that the programme never wrote.

Research from MDPI (2023) on infrastructure projects confirmed this: the quality of
stakeholder engagement is a robust predictor of project outcome, operating at project,
program, and enterprise levels. **[T2]**

The practical distinction:

- **Engagement as communication**: "Here's what we're building. Please provide
  feedback." (One-directional, information flows from project to stakeholders.)
- **Engagement as requirements engineering**: "Help us understand your work. What
  would need to be true for this system to help you?" (Bidirectional, information
  flows from stakeholders into project scope and design.)

Users who resist a system are not obstacles to be overcome. They are sensors
providing data about whether the system will work in practice. Excellent project
management treats resistance as signal, not noise.

### 3.3 Single-Point Accountability

Every major project failure studied in this investigation (Section 11) featured the
same structural defect: diffused accountability through committee governance.

Healthcare.gov had no single empowered project lead — decisions were made by
committee across CMS, contractor organizations, and political stakeholders. The FBI
Virtual Case File had committee governance and 5 CIOs in 4 years. The NHS NPfIT
concentrated governance in a central organization (Connecting for Health) that had
authority over everything but accountability for nothing — it could impose decisions
but could not deliver them.

The mechanism by which committee governance fails is predictable from organizational
theory:

1. **No escalation target.** When there is no single person accountable, problems
   that require cross-cutting decisions circulate between committee meetings, losing
   weeks each cycle.
2. **Diffused blame.** When everyone is responsible, no one is responsible. Committee
   members can attribute failure to other members' domains.
3. **Lowest-common-denominator decisions.** Committees optimize for consensus, which
   means avoiding decisions that any member objects to. This systematically selects
   for mediocre, uncontroversial choices rather than the best available option.
4. **Political dynamics.** Committee members represent constituent interests. The
   integrated project outcome is nobody's primary concern.

The counter-pattern, seen in successful recovery efforts (the Healthcare.gov "tech
surge," the FBI Sentinel project that succeeded after VCF's failure), is the
appointment of a single individual with authority over the integrated outcome —
someone who can make cross-cutting decisions, say no to scope additions, escalate
blockers to executives, and be fired if the project fails.

This does not mean dictatorial project management. The accountable individual
delegates extensively and empowers their team. But the *accountability* — the
question of "whose career depends on this succeeding?" — must have a single answer.

### 3.4 Team Composition and Leadership

#### Leadership Style

Research converges on situational/adaptive leadership as the most effective model,
not because it is a clever synthesis, but because projects genuinely move through
phases that require different leadership behavior. **[T2]**

**Transformational leadership** (inspiring vision, developing people, high autonomy)
works best for:
- Innovation-intensive projects
- Teams with high technical expertise
- Early phases where direction is being established
- Complex domains where emergence is expected

**Transactional leadership** (clear expectations, reward for performance, structured
accountability) works better for:
- Execution phases with well-defined deliverables
- High-risk environments requiring strict process adherence
- Teams with lower experience levels
- Predictable domains where efficiency matters more than innovation

The failure mode that appears repeatedly in case studies is **leadership style
inflexibility**: the micromanager who cannot give the experienced team autonomy; the
visionary who cannot shift to execution discipline when deadlines approach; the coach
who cannot make hard calls when the project is in crisis.

#### Conflict: The Type Matters More Than the Amount

Research published in the Journal of Applied Psychology identified a critical
distinction **[T2]**:

- **Task conflict** (disagreement about approach, technical decisions, scope
  priorities) is *positively* associated with team performance up to moderate levels.
  It surfaces different perspectives and produces better decisions. A team that agrees
  on everything is either homogeneous or suppressing dissent — both are dangerous.

- **Relationship conflict** (interpersonal friction, blame, status games) is
  *negatively* associated with team performance at all levels. Even small amounts
  of relationship conflict degrade collaboration, trust, and information sharing.

High-performing teams convert relationship conflict into task conflict — they maintain
the disagreement about substance while removing the personal dimension. This requires
active facilitation, particularly the ability to reframe "you're wrong" as "let's
examine the evidence for both approaches."

The practical implication for PM tools: retrospective and review features should
facilitate structured disagreement about approach and priorities while keeping
the focus on the work rather than the people.

### 3.5 The Autonomy Paradox

A 2022 study on autonomous software development teams found that teams switching to
autonomous structures saw value added increase by 39%, with customer satisfaction
ratings increasing 2.95%. McKinsey research reported that 85% of employees report
greater engagement under appropriate autonomy. Gallup found that micromanaged
employees are 3.2x more likely to quit within six months. **[T2-3]**

But autonomy without structure produces chaos. The ACM study on Scrum team
effectiveness (the most rigorous available, 5,000 developers, 2,000 teams) found
that team autonomy is a structural prerequisite for effectiveness — but only when
combined with management support, clear goals, and organizational infrastructure
for removing blockers. **[T2]**

The pattern: **high autonomy in *how* combined with high clarity in *what* and *why***.
Teams need the freedom to decide their implementation approach while having crystal
clarity on what outcome is expected and why it matters. This is the opposite of both
micromanagement (which constrains *how*) and absence of management (which fails to
define *what* and *why*).

---

## 4. Planning, Estimation, and the War Against Cognitive Bias

### 4.1 The Planning Fallacy Is Universal

Daniel Kahneman and Amos Tversky identified the planning fallacy in 1979: people
systematically underestimate time, cost, and risks of planned actions while
overestimating benefits. **[T1]**

This is not a tendency. It is a near-universal cognitive bias:

- In a study of students estimating their own task completion times, only 13%
  finished by their self-assigned 50% probability deadline. Only 45% finished by
  their 99% probability deadline. When people say "I'm 99% sure I'll finish by
  Friday," the actual probability is below 50%.

- Bent Flyvbjerg, studying thousands of real-world projects, documented staggering
  and persistent overruns across every domain and geography:
  - IT projects: **73% average cost overrun**
  - Olympic Games: **157% average overrun**
  - Transportation projects: **20-45% average overrun**
  - These figures hold across countries, decades, and organizational types

The mechanism is "inside view" thinking: when estimating a project, people imagine
the specific sequence of events for *this* project — how long each task will take,
what might go well — rather than consulting base rates from *similar past projects*.
The inside view is always optimistic because it models the planned scenario, not the
full distribution of possible scenarios including delays, scope changes, resource
unavailability, and integration failures.

### 4.2 Strategic Misrepresentation: It's Not Always Innocent

Flyvbjerg distinguishes two causes of underestimation **[T1]**:

1. **Optimism bias**: Genuine cognitive error. Project teams sincerely believe their
   project is different and will beat the odds. This is the planning fallacy operating
   automatically.

2. **Strategic misrepresentation**: Deliberate underestimation to win approval.
   Project sponsors know the real estimate would not be funded, so they submit a
   lower number to get the project started, planning to request additional funding
   once the organization is committed (sunk cost). This is rational deception in
   environments where projects compete for fixed budgets and the penalty for
   overruns is less severe than the penalty for not getting funded.

The critical insight is that both mechanisms produce the same result — systematically
optimistic estimates — but require different interventions. Optimism bias can be
partially addressed with better estimation methods (reference class forecasting,
historical data, pre-mortem exercises). Strategic misrepresentation can only be
addressed with governance changes: making the consequences of deliberate
underestimation career-threatening, and making it safe to submit honest estimates
that may be larger than the organization wants to hear.

### 4.3 The Ten Cognitive Biases That Kill Projects

Flyvbjerg's 2021 catalogue of the top ten behavioral biases in project management,
published in the peer-reviewed Project Management Journal, provides a comprehensive
threat model **[T1]**:

1. **Strategic misrepresentation** — Deliberate underestimation to win approval
2. **Optimism bias** — Genuine overestimation of positive outcomes
3. **Uniqueness bias** — "Our project is different from those statistics"
4. **Planning fallacy** — Inside view dominates over base rates
5. **Overconfidence bias** — Excessive certainty in own judgments
6. **Hindsight bias** — Past successes seem more predictable than they were
7. **Availability bias** — Overweighting vivid recent experiences
8. **Base rate fallacy** — Ignoring historical data for similar projects
9. **Anchoring** — First estimate becomes sticky regardless of new information
10. **Escalation of commitment** — Continuing failing projects to justify sunk costs

Each of these biases operates at the individual level, but they compound at the
organizational level. A project team exhibiting optimism bias submits estimates to
a governance board exhibiting anchoring (anchored to the already-optimistic estimates)
and escalation of commitment (continuing to fund a project they've already invested
in, even as evidence of trouble mounts).

### 4.4 Reference Class Forecasting: The Evidence-Based Fix

Reference Class Forecasting (RCF) is the method Kahneman and Lovallo proposed to
counteract inside-view estimation. Flyvbjerg operationalized it for practical use.
**[T1-2]**

The method:
1. Identify a **reference class** of similar past projects (same type, size, domain)
2. Build a **probability distribution** of actual outcomes for that class (what did
   time, cost, and scope actually look like?)
3. **Anchor** the current project's estimate to that empirical distribution
4. **Adjust** only for specific, documented factors that make this project genuinely
   different from the reference class

The UK HM Treasury adopted RCF for infrastructure planning. Empirical studies show
it reduces optimism bias by 15-30% in megaprojects. It has been tested in offshore
oil and gas, transportation, and IT contexts with consistent improvement in
estimation accuracy. **[T2]**

The practical challenge is defining the right reference class. "IT projects" is too
broad — a $50K internal tool and a $500M ERP replacement have nothing meaningful in
common. The reference class must be specific enough to be informative: "ERP
implementations for 500-2000 employee manufacturing companies," not "software
projects."

**Implication for tools**: A project management system that automatically captures
actual time, cost, and outcome data from completed projects — and makes this data
easily queryable for future estimation — enables reference class forecasting without
requiring statistical expertise. This is a high-value, low-effort feature that most
PM tools neglect.

### 4.5 Pre-Mortem: Imagining Failure Before It Happens

Gary Klein's pre-mortem technique, grounded in prospective hindsight research,
inverts the normal planning process **[T2]**:

Instead of asking "What could go wrong?" (which triggers optimism bias — people
minimize risks), the team imagines that the project has already failed and asks
"Why did it fail?"

The psychological mechanism: once failure is assumed as a premise, team members feel
socially safe to identify risks they would otherwise suppress (because raising risks
in normal planning is implicitly criticizing the plan). Research shows pre-mortems
surface 30% more risks than traditional risk identification sessions.

A structured pre-mortem:
1. The team is told: "It is 6 months from now. The project has failed spectacularly."
2. Each person independently writes down 3-5 reasons why it failed.
3. The team shares and groups the reasons.
4. Each high-frequency reason is assessed: can we prevent it? Can we detect it early?
   What would be the first visible sign?

This is cheap to implement, requires no tools beyond a meeting room, and produces
actionable risk data. A project management tool could formalize this as a project
initiation template with structured pre-mortem fields.

---

## 5. Methodologies: What the Evidence Says vs. What Vendors Sell

### 5.1 The Framework Wars Are Mostly Marketing

The project management industry has a financial interest in the Agile-vs-Waterfall
debate continuing indefinitely, because the debate drives certification purchases,
training revenues, and consulting engagements on both sides.

The evidence is less exciting:

**PMI Pulse 2024 [T3]**: The chosen project management approach does not
statistically impact project success. Fit-to-context matters more than method.

**Springer 2023 comparative study [T2]**: Methodology accounts for approximately
40% of activity variance. The remaining 60% is explained by individual designer
habits, project circumstances, and noise. This means *who does the work* and *what
the conditions are* matter more than *which process they follow*.

**DORA longitudinal data [T1-2]**: Does not prescribe a methodology. The metrics
that predict delivery success (deployment frequency, lead time, change failure rate,
recovery time) can be achieved through Scrum, Kanban, XP, or custom processes.

**The ACM Scrum study [T2]**: Scrum works when its prerequisites are met (team
autonomy, management support, frequent releases). It fails when they are not — which
is most implementations.

The honest conclusion from peer-reviewed evidence: **no methodology is universally
superior, and the choice of methodology matters less than the quality of execution
within whatever methodology is chosen**. Organizations that spend six months
evaluating frameworks would get better outcomes by spending that time building
psychological safety and improving their estimation practices.

### 5.2 The Cynefin Framework: Matching Method to Problem Type

The most useful tool for methodology selection is not a methodology at all — it is
a sense-making framework. Dave Snowden's Cynefin framework, published in Harvard
Business Review and extended through academic research, classifies problem domains
into five types **[T2]**:

**Clear (Simple)**: Cause-effect relationships are obvious. Best practices exist and
can be applied directly. Examples: routine maintenance tasks, standard procurement,
recurring IT operations. Appropriate approach: standardized process, checklists.

**Complicated**: Cause-effect requires analysis and expertise. Multiple valid
approaches exist, and expert judgment selects among them. Examples: enterprise
architecture design, system integration, complex reporting. Appropriate approach:
expert analysis → plan → execute (traditional PM works here).

**Complex**: Cause-effect is only apparent in retrospect. Outcomes emerge from
interactions that cannot be predicted. Examples: new product development, digital
transformation, organizational change, most non-trivial software. Appropriate
approach: probe → sense → respond (iterative, experimental — Agile works here).

**Chaotic**: No perceivable cause-effect. Immediate action is needed. Examples:
production outages, security breaches, crisis response. Appropriate approach:
act → sense → respond (stabilize first, then analyze).

**Confusion/Disorder**: You don't know which domain you're in. This is where most
organizations spend too much time, applying methods appropriate for Complicated
problems to Complex situations, or Complex approaches to Clear problems.

**Why this matters for methodology selection**: Academic extension (IJIM 2021) found
that project failure rates correlate with misclassification — specifically, treating
a Complex problem as Complicated (applying detailed upfront planning to an inherently
unpredictable situation). This misclassification is the most common error because
organizations *want* their problems to be Complicated (analyzable, plannable) rather
than Complex (emergent, uncertain). **[T2]**

**Most software projects sit at the Complex-Complicated boundary.** This means they
need elements of both structured planning (architecture, risk assessment, resource
allocation) and iterative discovery (prototyping, user feedback, incremental delivery).
The Agile-Stage-Gate hybrid that Cooper (2016) documented and validated is one
practical implementation of this insight.

### 5.3 Scrum: When It Works and Why It Usually Doesn't

The most rigorous empirical study of Scrum is Verwijs et al. (2023), published in
ACM Transactions on Software Engineering and Methodology — a 7-year mixed-methods
investigation across approximately 5,000 developers and 2,000 Scrum teams. **[T2]**

Their findings explain both Scrum's theoretical promise and practical failure:

**What makes Scrum teams effective (5 factors, 13 sub-factors):**
1. **Responsiveness** — the team's ability to adapt to changing information
2. **Stakeholder concern** — genuine interest in user outcomes, not just ticket closure
3. **Continuous improvement** — retrospectives that produce real change
4. **Team autonomy** — the team decides *how* to do the work
5. **Management support** — the organization provides infrastructure, removes blockers

**The single strongest predictor**: Frequent releases. Teams that do not release
frequently are less effective regardless of how well they score on other factors.

**Why Scrum usually fails**: Most organizations implementing Scrum do not actually
provide the prerequisites. Teams lack autonomy (managers assign work and dictate
solutions). Management "support" means surveillance, not blocker removal. Releases
are quarterly, not weekly. Retrospectives are cancelled when sprints are busy.

Ron Jeffries, one of the 17 Agile Manifesto signatories and co-creator of Extreme
Programming, coined the term "Dark Scrum" for this pattern: Scrum used as a
micromanagement tool, where sprint commitments become deadlines, velocity becomes
a performance metric, and daily standups become status reporting to managers.
Jeffries went further in 2018, writing "Developers Should Abandon Agile" — not
because agile is wrong, but because "the Agile Industrial Complex" has corrupted
the implementation to the point where the word is a liability.

Martin Fowler identified three central problems in his 2018 keynote on the "Agile
Industrial Complex" **[T4-5]**:
1. Imposing process on teams — contradicting "individuals and interactions over
   processes and tools"
2. Abandoning technical excellence — Agile conferences are dominated by project
   managers, not developers; TDD, refactoring, and CI have been sidelined
3. Certification mill dynamics — Scrum Alliance, Scrum.org, and Scaled Agile create
   economic ecosystems dependent on perpetual certification sales

### 5.4 Kanban: Mathematically Sound, Empirically Thin

Kanban's strength is its theoretical foundation. Unlike Scrum (which is a framework
designed by practitioners), Kanban's core mechanism — WIP limits reduce cycle time —
is derived from a mathematical theorem. **[T1 for the theorem, T3-4 for software
application]**

Little's Law (John Little, MIT, 1961) states:

```
Average WIP = Average Throughput x Average Cycle Time
```

This is not a heuristic or an observation — it is a formally proven theorem for
stable queueing systems. It means that for a given throughput, reducing WIP
*mathematically requires* reducing cycle time. If your team completes 10 items per
week (throughput) and has 20 items in progress (WIP), average cycle time is 2 weeks.
If you reduce WIP to 10, average cycle time drops to 1 week — mechanically,
necessarily.

**The caveat**: Little's Law requires a stable system in a steady state. Software
development is often neither. Teams that are forming, changing, or dealing with
high variability in task size will see deviations from the mathematical prediction.
But even in unstable systems, the *direction* is reliable: less WIP generally means
shorter cycle times and more predictable delivery.

The empirical evidence for Kanban in software, however, is thinner than its
theoretical elegance warrants. Kanban University's 2024 survey claimed teams
enforcing WIP limits improve delivery times by up to 37% — but this is a self-
reported vendor survey, not a controlled study. A Microsoft IT case study
demonstrated effectiveness for managing change requests, reducing cycle time
significantly. The Siemens Health Services case study showed a 42% reduction in
cycle time after switching from story points to flow metrics. But rigorous head-
to-head comparisons between Kanban and Scrum are scarce. **[T3-4]**

### 5.5 SAFe: The Most Adopted and Most Criticized Scaling Framework

SAFe (Scaled Agile Framework) is the most widely adopted scaling framework — 37%
of organizations using a scaling approach use SAFe. It is also the most criticized
by practitioners, academics, and even government institutions.

**The structural criticisms are serious:**

1. **PI Planning contradicts agile principles.** Program Increment Planning locks
   50-125 people into 8-12 week plans during a 2-day event. This is a large batch
   size — the antithesis of iterative feedback.

2. **Centralized decision-making.** Release Train Engineers, Solution Train Engineers,
   and Portfolio-level stakeholders concentrate decisions in ways that recreate the
   command-and-control structures agile was designed to replace.

3. **The US Air Force rejected it explicitly.** In December 2019, the Air Force's
   Chief Software Officer issued a memorandum "highly discouraging from using SAFe,"
   noting it is "not used by any successful commercial software organization."

4. **No peer-reviewed evidence for effectiveness.** Despite 2M+ certified
   professionals, there are no independent peer-reviewed studies validating SAFe's
   core mechanisms (PI Planning, ARTs, value streams).

**The nuanced assessment**: Christiaan Verwijs (whose ACM Scrum study is cited above)
conducted a balanced investigation and found that the evidence does not support the
extremely negative view many have of SAFe — but evidence for its superiority is
equally absent. 8 out of 10 SAFe adopters would not want to go back, but this may
reflect improvement over the *typically bad alternatives* it replaces (pure waterfall,
Prince2, or organizational chaos). Replacing something terrible with something
mediocre still feels like progress. **[T3]**

---

## 6. Metrics That Matter vs. Metrics That Deceive

### 6.1 DORA: The Gold Standard for Software Delivery

The DORA program (DevOps Research and Assessment), founded by Nicole Forsgren, Jez
Humble, and Gene Kim, is the closest software engineering has to clinical research.
Based on 32,000+ annual survey respondents and over a decade of longitudinal analysis,
its findings are published in "Accelerate" (Shingo Award winner) and annual reports
through Google Cloud. **[T1-2]**

**The five metrics (2025):**

| Metric | What It Measures | Elite Benchmark |
|--------|-----------------|-----------------|
| Deployment Frequency | How often code reaches production | Multiple times/day |
| Lead Time for Changes | Commit to production elapsed time | Less than 1 hour |
| Change Failure Rate | % of deployments causing incidents | 0-5% |
| Recovery Time | Time to restore service after failure | Less than 1 hour |
| Rework Rate (2025) | Ratio of unplanned fix deployments | Minimal |

**The most important finding**: Speed and stability are NOT a tradeoff. This is
counter-intuitive and contradicts decades of conventional wisdom that says "move fast
and break things" or "slow down for quality." DORA's data shows that elite performers
deploy frequently *and* have better change failure rates *and* recover faster.
Organizations that slow down deployments to improve stability get neither speed nor
stability — they get slow and fragile.

The mechanism: frequent, small deployments are inherently lower-risk than infrequent,
large deployments. A deployment touching 3 files is easier to understand, test,
review, and roll back than a deployment touching 300 files. Frequent deployment also
means faster feedback: if something breaks, you know it was one of the 3 files
changed in the last hour, not one of 300 files changed in the last month.

**2024 findings on AI (critical)**: AI adoption is associated with a **1.5% decrease
in throughput and 7.2% decrease in stability**. This directly contradicts the vendor
narrative of AI as a productivity multiplier. 39% of developers outside Google trust
AI-generated code quality only "a little" or "not at all." AI has not meaningfully
reduced burnout. The honest state: AI helps with writing assistance but measurably
hurts delivery quality in current implementations. **[T1-2]**

**2024 findings on platform engineering**: Internal developer platforms increased
individual productivity by 8% and team productivity by 10%, but decreased change
throughput by 8% and stability by 14%. The productivity gains from standardized
tooling are partially offset by coordination overhead. **[T2]**

### 6.2 Flow Metrics: What to Measure Instead of Velocity

Flow metrics are derived from Lean manufacturing theory and queueing theory. They
have stronger mathematical and empirical foundations than Agile estimation metrics
(story points, velocity). **[T1 for theory, T3-4 for software application]**

**The four core flow metrics:**

**Cycle Time** — elapsed time from when work *actively starts* on an item to when
it is *done*. This measures your team's execution speed. It is objective (based on
timestamps, not estimates), comparable over time, and impossible to game without
actually getting faster.

Practically: if your team's median cycle time is 5 days and a stakeholder asks "when
will this be done?", the honest answer is "based on our historical data, about 5 days
after we start it, with 85% confidence it will be within 8 days." This is far more
useful than "we'll try to fit it into the next sprint."

**Lead Time** — elapsed time from when an item is *requested* (enters the backlog)
to when it is *delivered*. This measures the total wait-plus-work time the customer
experiences. The gap between lead time and cycle time reveals how long items wait
before anyone starts working on them — a queue that is invisible in most PM tools.

**Throughput** — the number of items completed per unit time (typically per week or
per sprint). This is the simplest metric and often the most useful for forecasting.
If your team completes an average of 8 items per week with a standard deviation of 2,
you can forecast delivery dates probabilistically without any estimation ceremony at
all.

**WIP (Work In Progress)** — the number of items currently in active work states
(not in backlog, not in done). WIP is the lever that controls the other three metrics
via Little's Law. Reducing WIP reduces cycle time; increasing WIP increases it.

**Cumulative Flow Diagram (CFD)** — a stacked area chart showing the number of items
in each state over time. The vertical distance between bands shows WIP per state.
The horizontal distance shows approximate cycle time. The slope of the "done" band
shows throughput. A CFD that shows widening bands reveals accumulating WIP — work
is entering the system faster than it is leaving. This is the single most
information-dense visualization in project management: one chart shows flow health,
bottlenecks, WIP trends, and throughput simultaneously.

### 6.3 Story Points: A Well-Intentioned Mistake?

Story points were designed as a relative estimation tool — a way for teams to
communicate effort without committing to hours. In theory, this is reasonable:
estimating that task A is "about twice as hard as task B" is more reliable than
estimating that task A will take "16 hours."

In practice, story points have become one of the most dysfunctional metrics in
software development **[T4-5]**:

- **They are subjective.** A "5" on one team is an "8" on another. Cross-team
  comparison is meaningless, but management does it anyway.
- **Velocity becomes a performance metric.** "Your velocity was 40 last sprint,
  why is it 35 this sprint?" Teams learn to inflate estimates to protect velocity.
- **Quality suffers.** When commitment (story points per sprint) becomes a target,
  teams cut corners to protect the burndown chart.
- **They require calibration rituals.** Planning poker, relative sizing, reference
  stories — all consuming meeting time for a metric of questionable value.

**The #NoEstimates evidence**: Vasco Duarte's empirical experiment (2011-2012) compared
story-point-based forecasts to raw throughput-based forecasts on the same project.
Story point forecasts deviated 20% from actual results. Throughput forecasts deviated
4%. This is a single practitioner's experiment, not a controlled trial, but it has not
been challenged with counter-evidence in over a decade. **[T4]**

**The Siemens Health Services case study**: After years of story points and velocity
without achieving the promised transparency, Siemens switched to WIP, cycle time, and
throughput. Result: 42% reduction in cycle time and significant improvement in
operational efficiency. **[T3]**

**Monte Carlo simulation** — the most sophisticated alternative to estimation — uses
historical throughput distributions to generate probabilistic forecasts. Instead of
"we'll deliver in sprint 7," the output is "there is an 85% probability we'll deliver
by March 15." This is both more honest (it acknowledges uncertainty) and more useful
(it gives stakeholders a confidence interval rather than a false promise).

### 6.4 Burndown Charts: Useful Rhythm, Dangerous Decision Tool

Burndown charts (remaining work over time against a projected line) are ubiquitous in
Agile practice and provide useful sprint rhythm visibility. But they carry well-
documented problems as decision tools **[T4-5]**:

- **No quality context.** A fast burndown can mean excellent work or cut corners.
  The chart looks the same either way.
- **Perverse incentives.** Teams learn to close tickets rather than complete
  meaningful work. Splitting a ticket into three trivial sub-tickets that can be
  closed quickly looks great on a burndown while adding zero value.
- **Misleading when scope changes.** If scope increases mid-sprint (items added to
  the sprint backlog), the burndown appears to slow or reverse even if the team's
  throughput is constant. This creates false alarm.
- **Past-focused.** A burndown shows where you've been, not where you're going. By
  the time a problematic trend is visible, the sprint is usually too far gone to
  correct.

**Better alternatives for decision-making**: Cumulative flow diagrams for flow health,
cycle time scatter plots for predictability, and throughput histograms for capacity
planning. Retain burndown for team ceremony and rhythm, but make real decisions with
flow metrics.

### 6.5 Earned Value Management: Powerful but Narrow

EVM integrates scope, schedule, and cost into a single measurement framework. It has
the strongest independent evidence base of any PMI tool, particularly in large
government and defense contracts. **[T2]**

**What EVM does well:**

The core metrics — Cost Performance Index (CPI = Earned Value / Actual Cost) and
Schedule Performance Index (SPI = Earned Value / Planned Value) — are reliable
predictors as early as 15-20% into a project lifecycle. Research on 400+ DOD programs
found that the cumulative CPI does not significantly improve between 15% and 85%
completion. If your CPI is 0.85 at the 20% mark, it will likely still be around 0.85
at the 80% mark. **[T2]**

This means EVM provides genuine early warning — the strongest single argument for
its adoption.

**Where EVM fails:**

- **Dynamic environments.** EVM forecasting assumes future performance mirrors past
  performance. When requirements change, resources shift, or technical risks
  materialize, the forecast becomes unreliable.
- **Cultural dependency.** A 2024 study ("EVMS is a Team Sport") found that EVM
  outcomes depend heavily on organizational culture, team adoption, and leadership
  support — not the system itself. EVM produces data; it does not produce decisions.
- **Implementation cost.** EVM requires work breakdown structure development, baseline
  maintenance, and data collection systems. For smaller projects or projects with
  evolving requirements, implementation costs may exceed benefits.
- **Government adoption gaps.** GAO audits of NASA found that more than half of major
  projects lacked certified EVM systems despite being required by policy. When even
  the organizations that mandate EVM cannot implement it consistently, the practical
  barriers are clearly significant.

**Honest assessment**: EVM is valuable for well-defined, large-budget projects with
stable scope (defense, infrastructure, construction). Its utility decreases
significantly for software projects with evolving requirements, projects under $20M,
and organizations lacking EVM culture. For most software teams, flow metrics (cycle
time, throughput) provide similar early-warning value with much lower overhead.

---

## 7. Governance: How Decisions Get Made (or Avoided)

### 7.1 The Decision-Making Deficit

Inefficient decision-making processes cost a typical Fortune 500 company approximately
530,000 days of managerial time annually, equivalent to $250M in wages (McKinsey
Organizational Health research). **[T3]** While the specific figure should be treated
with caution (McKinsey sells advisory services), the qualitative finding is consistent
with broader organizational research: most organizations are far better at producing
information than at acting on it.

In project management, the decision-making deficit manifests in three patterns:

**Analysis paralysis**: Endless evaluation of options, technology comparisons,
stakeholder consultations, and risk assessments that delay the start of work. The
cost of the evaluation exceeds the cost of making an imperfect decision and correcting
later. This is particularly destructive during requirements definition (attempting
perfect requirements before development begins) and technology selection (multi-month
vendor evaluations that produce documents rather than decisions).

**Escalation avoidance**: PMs who know a decision needs to be made at a level above
them but continue attempting to resolve it themselves, deferring escalation because
escalation feels like failure. Each week of avoidance narrows the remaining options
and increases the cost of the eventual decision.

**Consensus paralysis**: Governance bodies that require unanimous agreement, producing
decisions that everyone can tolerate but no one champions. The lowest-common-
denominator outcome satisfies the governance process while failing the project.

The antidote is explicit decision frameworks with **timeboxes**: "We will make this
decision by Friday with the information we have. If the decision proves wrong, we
will correct it at the next review point." This requires organizational comfort with
reversible decisions — recognizing that the cost of a wrong decision that can be
corrected is almost always lower than the cost of delayed decision.

### 7.2 Stage-Gate: When Formality Helps and When It Kills

Robert Cooper's Stage-Gate model structures projects as sequential phases separated
by gates — formal review points where continuation, modification, or cancellation
is decided. **[T2]**

**Where Stage-Gate excels:**
- Physical product development (manufacturing, pharmaceuticals)
- Regulated industries requiring compliance checkpoints
- Environments where requirements can be substantially defined upfront
- Portfolio governance requiring structured investment decisions

**Where Stage-Gate fails:**
- Software development. Research found that "adoption of Stage-Gate principles is
  negatively associated with speed and cost performance" in software. The reason is
  architectural: software requirements are discovered through development. Stage-Gate
  assumes requirements are knowable before development begins — an assumption that
  does not hold for novel software.

**The zombie project problem**: Gate decisions are meant to be genuine go/kill
decisions. In practice, organizational politics frequently turn gates into reporting
ceremonies where continuation is predetermined. No governance body wants to be the
one that killed a project a VP is championing. The result: "zombie projects" that
should have been killed consume resources that could have been redirected to
successful initiatives.

Research consistently finds that organizations are **better at starting projects
than killing them**. The asymmetry between go and stop decisions is both psychological
(sunk cost reasoning: "we've already invested $2M") and political (killing a project
means someone's initiative failed). Excellent governance requires pre-defined kill
criteria established at project initiation, when the emotional and political
investment is low.

### 7.3 Rolling Wave Planning: Honest Planning for Uncertain Environments

Rolling wave planning treats planning as an ongoing activity: near-term work is
planned in detail; future work is planned at progressively higher abstraction levels.
As the project progresses and uncertainty resolves, future waves are planned in more
detail.

This is the most intellectually honest planning model for complex projects because
it does not pretend to know things it cannot know. A project starting in March cannot
meaningfully plan August's tasks at the task level — too much will change. But it can
plan August at the milestone level: "By August, we expect to have completed
integration testing and be ready for user acceptance."

**The failure mode**: Without strong governance, rolling wave becomes an excuse for
no planning. "We'll figure it out when we get there" is not rolling wave planning
— it is the absence of planning wearing rolling wave's clothes. Genuine rolling wave
requires genuine up-front investment in: architectural decisions that constrain all
future work, risk identification that shapes contingency reserves, and constraint
mapping that identifies external dependencies regardless of when they'll be resolved.

### 7.4 The Agile-Stage-Gate Hybrid

Academic research (Cooper 2016, Journal of Product Innovation Management) and
practitioner evidence converge on hybrid approaches as the practical optimum for
most complex programmes. **[T2]**

The hybrid preserves Stage-Gate's portfolio governance (structured investment
decisions at gates) while replacing sequential phases with iterative sprints
(allowing requirements discovery and incremental delivery between gates).

Sprint-based development within gate-bounded phases was positively associated with
quality, on-time delivery, and on-budget completion in empirical studies, while pure
Stage-Gate was negatively associated with speed and cost.

**The integration challenge** is the interface between iterative team-level work and
periodic gate reviews. Agile teams generating sprint throughput data need to translate
that into portfolio-level language that gate reviewers can act on: value delivered,
risk consumed, revised completion forecasts, and go/kill recommendations. This
translation layer is where hybrid implementations most commonly fail — the team
speaks in story points and cycle time while the governance board speaks in budgets
and milestones.

---

## 8. Portfolio Management: The Organizational Layer

### 8.1 The Overcommitment Problem

The biggest portfolio-level failure, identified consistently across research
traditions, is **overcommitment**: organizations approve more projects than their
resource pool can support. **[T2]**

The mechanism is straightforward. Each project is justified individually: the
business case is sound, the resources appear available, the timeline is feasible.
But the organization evaluates projects in isolation, without accounting for the
cumulative demand on shared resources (developers, testers, subject matter experts,
infrastructure).

The result: every developer is allocated to 3 projects, each of which assumes they
are full-time. Context-switching between projects — rebuilding mental models, attending
three sets of meetings, managing three sets of stakeholder expectations — consumes
20-40% of productive time, per operations research and simulation studies.

Eli Goldratt's Critical Chain work and subsequent empirical validation showed that
multitasking between projects increases total duration by 20-40% compared to
sequential execution. **[T2]** Three projects each estimated at 3 months, executed
simultaneously, do not complete in 3 months — they complete in 5+ months, each,
because the interleaving destroys focus and creates coordination overhead.

**The fix is organizational, not technical**: a portfolio governance body that
constrains the total number of active projects to organizational capacity. This
requires the politically difficult act of saying "no" or "not yet" to legitimate
projects that exceed capacity. PM tools can help by making cross-project resource
utilization visible — showing that the organization has committed 180% of its
developer capacity across active projects, for example — but the *decision* to
constrain WIP is a leadership decision, not a software feature.

### 8.2 Strategic Alignment: Necessary but Insufficient

Hansen and Svejvig's 2023 synthesis of seven decades of PPM research found that
strategic alignment — ensuring projects support organizational strategy — is necessary
but insufficient. **[T1]**

Organizations also need **portfolio agility**: the ability to add, remove, and
re-prioritize projects as strategy evolves. Annual planning cycles that lock project
portfolios for 12 months create rigidity that prevents the organization from
responding to market changes, competitive moves, or internal learning.

The most effective portfolio management approaches combine:
- **Strategic alignment** at project selection (does this project advance our strategy?)
- **Capacity governance** across the portfolio (do we have resources to do this?)
- **Continuous re-prioritization** based on new information (should this still be our
  priority given what we've learned?)
- **Explicit kill criteria** (under what conditions will we stop this project?)

### 8.3 PPM Tools Only Work with Mature Processes

A ScienceDirect study (2020) found that PPM software tools only deliver performance
benefits when an organization's portfolio management processes are mature. **[T2]**

Organizations with low process maturity — those without consistent project
categorization, resource tracking, or governance cadence — showed **no performance
improvement** from PPM software. The tool cannot create the process; it can only
amplify a process that already exists.

This is a critical insight for Odoo: adding portfolio dashboard features without
addressing the underlying governance process will produce pretty charts that nobody
acts on. The features need to be designed to *guide organizations toward process
maturity*, not just serve organizations that are already mature.

### 8.4 The PMO Identity Crisis

Gartner found that 68% of stakeholders perceive their PMOs as bureaucratic. Only 40%
of projects meet schedule, budget, and quality goals even where PMOs exist. **[T3]**

The fundamental problem: most PMOs are built for **compliance and reporting** (did you
fill out the risk register? Is your status report current?) rather than **value
delivery** (is this project actually going to achieve its business case? Should we
continue investing?).

Gartner's research identifies a key failure: PMOs routinely provide the wrong
information to senior managers. They over-detail at the operational level (here are
53 tasks with their status) when executives need strategic summaries (here are the
3 decisions you need to make this week, with recommendations). The fix is not a
better reporting template — it is understanding what decisions senior managers need
to make and structuring information around those decisions.

The PMOs that deliver value have evolved from "project police" to "decision support
infrastructure." They spend less time checking compliance and more time synthesizing
cross-project insights, identifying resource conflicts before they cause delays, and
advising governance boards on portfolio health. This evolution is the key challenge
for Odoo's portfolio features.

---

## 9. Risk Management: From Ritual to Culture

### 9.1 The Evidence: Risk Culture vs. Risk Process

A meta-analysis in the International Journal of Project Management asked: "Does risk
management contribute to IT project success?" The answer: yes, **but only when
practiced genuinely**. Organizations that practice risk management ritually —
maintaining risk registers as compliance artifacts, reviewing them in meetings without
updating them, identifying risks without response plans — see no benefit. Organizations
with genuine risk *culture* — where identifying a risk is valued rather than punished,
where response plans are executed and tracked, where risk discussions are ongoing
rather than periodic — see measurable improvement. **[T2]**

The distinction between ritual and culture maps directly onto psychological safety.
A risk register is only as useful as the honesty of the people filling it in. In
organizations where raising risks is perceived as "being negative" or "not being a
team player," the risk register will contain sanitized, non-threatening risks
("market conditions may change") rather than the actual threats ("the lead developer
is job-hunting and if they leave we lose six months of knowledge"). The tool is not
the problem — the culture is.

### 9.2 What a Useful Risk Practice Looks Like

Based on synthesis across the PMI research, academic meta-analyses, and failure case
studies, a risk management practice that actually improves outcomes has these
characteristics:

**Risk identification is continuous, not periodic.** Risks do not appear on schedule.
The most dangerous risks are the ones that emerge between formal reviews. Teams need
a low-friction way to log risks as they discover them — ideally as easy as creating
a task.

**Every risk has an owner.** Unowned risks are unfixed risks. The owner is the person
responsible for monitoring the risk and executing the response plan if the risk
materializes. This is distinct from the PM — the PM tracks the risk register, but the
risk owner is the person closest to the technical or business domain where the risk
lives.

**Response strategies are concrete and budgeted.** "Mitigate by monitoring" is not a
response strategy. "Conduct load testing with 10,000 concurrent users by March 15,
allocated 3 developer-days, escalate to architecture team if P95 latency exceeds
200ms" is a response strategy. The difference is that the second one can be verified,
tracked, and executed.

**Probability and impact are assessed, not just listed.** A risk register that lists
risks without probability and impact assessment is a worry list, not a management
tool. The classic probability x impact matrix, despite its simplicity, enables
prioritization: high-probability, high-impact risks demand immediate action;
low-probability, low-impact risks can be accepted.

**Risk trends are tracked over time.** The total risk exposure of a project should
decrease over time as risks are mitigated, transferred, or resolved. If total risk
exposure is *increasing* — more risks are being identified than resolved, or existing
risks are becoming more probable — the project is in trouble regardless of what the
burndown chart says.

**The pre-mortem technique is integrated.** As described in Section 4.5, pre-mortems
surface risks that normal risk identification misses because they make it socially
safe to identify uncomfortable truths. Making pre-mortem a standard step in project
initiation is one of the highest-value, lowest-cost improvements an organization can
make.

---

## 10. Continuous Improvement: Why Organizations Don't Learn

### 10.1 The Lessons-Learned Paradox

Every project management methodology prescribes lessons-learned activities. Every
organization claims to capture lessons. And yet the same failure patterns recur on
project after project, organization after organization, decade after decade. The
planning fallacy persists. Scope creep persists. Status theater persists. Single
points of failure persist. Why?

The gap between lessons documented and lessons applied is one of the most durable
problems in the field. The mechanism is well-understood even if the solution is not:

**Timing failure.** Lessons are captured at the end of projects, when team members
are either celebrating completion or rushing to their next assignment. The people who
experienced the failure are rarely the people starting the next project. The
organizational memory that could transfer insights between projects does not exist in
most organizations — it existed in the heads of people who have moved on.

**Format failure.** Lessons are written for archival, not for use. A 20-page post-
mortem document deposited in a SharePoint folder is not a useful artifact for a PM
starting a new project. The knowledge needs to be in the form that people naturally
reach for: checklists ("before you start, verify that..."), templates ("here's how we
structured the risk register on similar projects"), and decision frameworks ("when
faced with X, consider Y because Z happened last time").

**Organizational siloing.** Lessons captured in Project A's documentation are
invisible to the team starting Project B in a different department. There is no
cross-cutting knowledge infrastructure that makes one project's learning available to
all subsequent projects. Each team starts from scratch, repeating discoveries and
mistakes that the organization has already paid for.

**No accountability for application.** Organizations measure whether lessons were
documented (compliance). They never measure whether they were applied on subsequent
projects (impact). The incentive is to produce the document, not to use it. This is
the knowledge management equivalent of status theater: the form is satisfied while
the substance is empty.

### 10.2 What Actually Works

Organizations that successfully transfer project learning share these characteristics,
identified across knowledge management research **[T2-3]**:

**Continuous capture, not post-project capture.** Lessons are collected throughout
the project via regular retrospectives, not saved for a single post-mortem. This
captures insights while they are fresh and while the team is intact.

**Knowledge organized by decision type, not by project.** "Lessons from Project
Alpha" is useful only to people who know about Project Alpha. "Things to consider
when estimating database migration effort" is useful to anyone doing a database
migration. The organizing principle must be the *problem type*, not the project
that encountered it.

**Application checkpoints at initiation.** Before a new project starts, a structured
step asks: "What has this organization learned about projects of this type?" This
requires a searchable knowledge base organized by project characteristics (domain,
size, technology, customer type) — not a filing cabinet of project-specific documents.

**Retrospectives with follow-through verification.** The most common failure of
retrospectives is not the retrospective itself — it is the absence of follow-through.
A retrospective produces five action items. Two are assigned. None are completed
before the next retrospective. After three iterations, the team rationally concludes
that retrospectives are theater.

The evidence-based prescription: retrospectives should produce **no more than 2-3
actions**. Each action is assigned to a specific person with a specific completion
date. The **first agenda item of the next retrospective** is verifying completion of
prior actions. Actions that are repeatedly carried forward without completion are
either not important enough to do (in which case, drop them) or blocked by something
the team cannot control (in which case, escalate).

### 10.3 The Deeper Problem: Project Amnesia

The fundamental issue connecting lessons learned, retrospectives, and knowledge
management is organizational. Most organizations treat projects as **discrete,
independent events** rather than **instances of a repeating organizational capability**.

A manufacturing plant that produces a defective batch investigates the defect, fixes
the production process, and expects subsequent batches to reflect the fix. The
*process persists* between batches — it is the durable asset that gets better over
time.

A project organization that delivers a failed project produces a lessons-learned
document, files it, and starts the next project with the same processes, tools, and
organizational patterns that caused the first failure. There is no persistent
*process* that subsequent projects run through and that improves over time.

Closing this gap requires what the knowledge management literature calls "absorptive
capacity" — organizational infrastructure that converts individual project experience
into institutional practice. This includes:
- A PM methodology that is updated based on project outcomes (not static documentation)
- Communities of practice across project teams (where PMs share challenges and
  solutions informally)
- Explicit investment in knowledge curation (a role or team responsible for making
  lessons findable and useful)
- Templates and checklists that encode lessons into workflow (so applying lessons
  is the default, not a discretionary effort)

---

## 11. Lessons from Catastrophic Failures

### 11.1 Healthcare.gov (2013)

**Budget**: $56M initial -> $209M actual (273% increase).
**Outcome**: Catastrophic launch failure, months of remediation, political crisis.

Healthcare.gov is a textbook case of management failure with sound architecture. The
Brookings Institution analysis emphasized that the hub-and-spoke architecture
connecting state systems was reasonable. The failure was almost entirely managerial.

**Root cause 1: No single accountable leader.** CMS never assigned one empowered
project lead. Decisions were made by committee. The GAO documented CMS's failure to
follow four basic Software Engineering Institute practices: scheduling, effort
estimation, data monitoring, and milestone reviews. There was no one person who could
say "we are not ready to launch" with the authority to delay.

**Root cause 2: Requirements defined too late.** Contractors did not receive
substantial specifications until March 2013 — seven months before the legally mandated
October launch. CMS issued task orders when the number of participating states and
projected enrollment were both unknown. This is the planning equivalent of building
a house without knowing how many rooms it needs.

**Root cause 3: Perverse contract incentives.** Cost-reimbursable contracts meant
contractors were paid for hours regardless of outcome, removing the primary incentive
to contain scope or flag problems early.

**Root cause 4: Testing at non-representative scale.** End-to-end testing with
hundreds of concurrent users instead of the 50,000+ expected on launch day. This is
not a budget shortcut — it is a fundamentally different test that verifies nothing
about production behavior.

**Root cause 5: No contingency planning.** CMS management was aware of problems
months before launch but declined to adjust plans. There was no phased rollback plan,
no contingency for partial functionality, no Plan B. When launch failed, there was
nowhere to fall back to.

### 11.2 Boeing 737 MAX / MCAS (2018-2019)

**Impact**: 346 deaths across two crashes.
**Root cause in one sentence**: Financial pressure caused Boeing to use software
(MCAS) to mask a hardware problem (aerodynamic instability from larger engines)
rather than redesign the airframe.

This case represents the most severe consequence class of PM failure: a system
approved for operational use that killed people because of undisclosed design
decisions made under commercial pressure.

Boeing had contracted with Southwest Airlines at terms including approximately $1M
per-plane rebate if the MAX required simulator training. This created a direct
financial incentive to classify MCAS as a minor modification rather than a novel
system. The IEEE Spectrum analysis is pointed: "Boeing tried to mask a dynamic
instability with a software system." Software should not be used to paper over
intractable hardware problems.

MCAS was redesigned during development to use a single angle-of-attack sensor
(original design used two). Airlines and pilots received no information about MCAS.
The failure mode analysis assumed MCAS would activate only once per event. Both
crash flights saw repeated, uncontrollable activation.

The organizational root cause was a documented culture shift from "the engineers'
company" to a finance-led organization following the 1997 McDonnell Douglas merger.
Safety culture eroded incrementally — each individual decision appeared defensible
while the aggregate outcome was catastrophic.

**Lesson for PM**: Teams on systems where failures have severe consequences must have
organizational protection to escalate technical concerns without career risk. This is
psychological safety applied to safety engineering. When teams cannot report problems,
the problems do not disappear — they transfer to customers.

### 11.3 UK NHS National Programme for IT (NPfIT, 2003-2011)

**Cost**: £10B+ for a programme that never delivered its primary objective.
**Verdict**: "One of the worst and most expensive contracting fiascos in public
sector history" (UK Public Accounts Committee).

**Root cause 1: Top-down design with no user ownership.** The programme was conceived
at Downing Street and handed to 300+ NHS Trusts with different workflows, existing
systems, and patient populations. Clinicians — the people who would actually use
the system — were not involved in requirements definition. When they resisted, their
resistance was treated as a change management problem rather than requirements data.

**Root cause 2: Monolithic architecture for heterogeneous reality.** A single
national system for 300+ organizations with different needs is technically and
organizationally naive. The architecture assumed uniformity that did not exist.

**Root cause 3: Adversarial contractor relations.** Terms described as "considerably
harsher than had ever been seen in government or private sector." Key vendors
(including Accenture) eventually walked away. When contractors optimize for contract
compliance rather than delivery, the project gets documentation, not software.

**Root cause 4: No phased delivery.** Big-bang implementation with no intermediate
milestones at which partial success could have been preserved. When the whole thing
failed, nothing was saved.

### 11.4 FBI Virtual Case File (2001-2005)

**Cost**: $170M, zero usable software delivered.

400 change requests against an 800-item requirements document. 5 CIOs in 4 years.
Committee governance. Big-bang deployment planned.

**The natural experiment**: The subsequent Sentinel project, launched after VCF's
failure, **succeeded** in 2012. Sentinel used Agile development, incremental
delivery, narrowed scope, and professional programme management. The contrast between
VCF and Sentinel is as close to a controlled experiment as project management gets.

### 11.5 Cross-Cutting Patterns

Across all four failures, five patterns recur:

1. **Accountability void.** Every failure had governance committees. None had a single
   accountable individual. Process sophistication is not a substitute for personal
   accountability.

2. **Information suppression.** Every failure had a moment — often months or years
   before the visible catastrophe — when the information needed to avert disaster
   existed somewhere in the system but did not reach decision-makers. Psychological
   safety failures, status theater, and escalation avoidance all contributed.

3. **Unmanaged pressure.** Commercial timelines (Boeing), political deadlines
   (Healthcare.gov), national ambition (NHS), and post-crisis urgency (FBI) all
   created pressure that overrode technical reality. When "we must deliver by X"
   becomes non-negotiable, the only variables left are scope and quality — and
   cutting those produces systems that fail.

4. **Organizations are better at starting than stopping.** None of these projects
   were cancelled early enough. Each accumulated sunk costs that made cancellation
   politically impossible, until the cost of continuation exceeded the cost of the
   initial investment.

5. **The gap between documented practice and actual practice.** None of these
   organizations lacked PM methodology. They failed because methodology was documented
   but not followed, or followed ceremonially while actual work happened differently.

---

## 12. Modern Practices: What's Real and What's Hype

### 12.1 OKRs: Goals on Steroids, For Better and Worse

OKRs (Objectives and Key Results), developed by Andy Grove at Intel in the 1970s and
popularized by John Doerr at Google in 1999, are a goal-setting framework where
qualitative Objectives are measured by quantitative Key Results.

The evidence base is **Tier 3-4**: mostly case studies and consultant reports, not
controlled studies. Academic goal-setting theory (Locke & Latham) provides theoretical
support — specific, challenging goals improve performance — but also generates the
strongest warnings.

**The counter-evidence is serious.** "Goals Gone Wild" (2009), published by
researchers from HBS, Wharton, and Kellogg, documented systematic side effects of
prescribing specific goals **[T1]**:
- Narrow tunnel vision on goal areas at the expense of non-measured work
- **Increased unethical behavior** when goals are specific and challenging
- Distorted risk preferences (gambling for the goal)
- Corrosion of organizational culture
- Reduced intrinsic motivation
- Real cases: Sears employees charging customers for unnecessary repairs to meet
  service revenue targets; Bausch & Lomb falsifying financials to meet targets

**OKR failure rate**: 60% of organizations struggle with implementation. 71% admit
they have not mastered OKRs despite using them. The stretch-goal principle ("celebrate
70% achievement") requires high psychological safety to function — in cultures where
failure has career consequences, stretch goals cause learned helplessness. **[T3-4]**

**Honest assessment**: OKRs likely help in organizations with high psychological
safety, strong data infrastructure, and leadership that genuinely treats missing
targets as information rather than failure. They are likely harmful when used for
individual performance evaluation, in cultures that punish failure, or when the
Key Results incentivize local optimization at the expense of system health.

### 12.2 AI in Project Management: The Hype vs. DORA Reality

**Market hype**: AI in PM market projected to grow from $3B to $14.5B by 2034.

**What works now (2025)**: Natural language summaries of threads and tickets,
AI-assisted writing for status updates and task descriptions, issue auto-
categorization and duplicate detection, code explanation and documentation generation.

**What DORA actually found (2024) [T1-2]:**
- 75.9% of developers use AI for daily tasks
- 75% report positive productivity impact (perception)
- But: a 25% increase in AI adoption correlates with only **2.1%** productivity gain
  and **2.6%** satisfaction gain — tiny effect sizes
- AI adoption is associated with a **1.5% decrease** in throughput and **7.2%
  decrease** in stability
- 39% of developers outside Google trust AI code quality "a little" or "not at all"
- AI has not meaningfully reduced burnout
- Stack Overflow 2025: 45% of developers say debugging AI-generated code is more
  time-consuming than writing from scratch

The vendor narrative of AI as a transformative productivity multiplier is not
supported by the best available evidence. The reality is more modest: AI is a useful
writing assistant that slightly hurts delivery quality in current implementations.
This gap between marketing and evidence should make PM tool builders cautious about
AI-first features — the risk is building features around capabilities that do not
yet deliver measurable value.

### 12.3 Remote/Distributed Teams: The Evidence Is In

The pandemic created a natural experiment at global scale, producing unusually rigorous
research.

**Stanford/Trip.com RCT (2024) [T1]**: The largest controlled study — 1,600 workers
randomly assigned to hybrid (2 days remote) vs. full in-office. Findings:
- Hybrid workers were equally productive and equally likely to be promoted
- Resignations fell 33% among hybrid workers
- Before the experiment, managers predicted remote would hurt productivity (-2.6%);
  after the experiment, they revised to a positive effect (+1.0%)

**Evidence-backed practices:**
1. Trust as foundation — transparent communication, distributed leadership
2. Documentation as infrastructure — GitLab's 12,000-page handbook is the canonical
   example of documentation as first-class engineering asset
3. Asynchronous default — 76% of employees report more distraction on video calls
   than in-person. Default to async; reserve synchronous for high-complexity
   coordination
4. Active boundary management — explicit work-stop times to prevent work-life
   collapse
5. Quarterly in-person gatherings — sufficient for most teams to maintain social bonds

### 12.4 Work Management Platform Analysis

Modern platforms have converged on a common core while differentiating by persona:

**Universal features**: Task management, multiple views (Kanban/list/Gantt/calendar),
automations, integrations, reporting, notifications.

**Differentiation**:
- **Jira**: Deep Agile (sprints, backlogs, burndown), developer ecosystem integration
- **Linear**: Speed (3.7x faster than Jira), opinionated simplicity, keyboard-first
- **Asana**: Cross-functional orchestration, portfolio/goal management, clean UX
- **Monday.com**: Visual customization, broad use-case flexibility
- **ClickUp**: Maximum feature density (time tracking, docs, whiteboards, sprints)
- **Notion**: Wiki + databases + projects unified, extreme flexibility

**The Linear counter-trend is instructive**: Linear deliberately rejects feature
parity with Jira. Its design philosophy is "software should be fast, focused, and
opinionated." 150,000+ teams use it, primarily startups and high-performance
engineering organizations. Developer satisfaction: 4.6/5 vs. Jira's 3.2/5.

This suggests that **less-is-more can be a viable PM tool strategy**. Each feature
added increases complexity, learning curve, and cognitive load. The right question is
not "does a competitor have this feature?" but "does the evidence support this feature
improving project outcomes?" If the answer is no or unclear, the feature imposes cost
without delivering value.

---

## 13. Odoo Project Module: Current State Assessment

### 13.1 What Odoo Does Well

Odoo's project module has genuine strengths that no dedicated PM tool can match:

**Native ERP integration** — The ability to go from sales order to project to
timesheet to invoice without leaving the system is Odoo's unique competitive
advantage. Jira cannot do this. Asana cannot do this. Monday.com cannot do this.
This integration is not just convenient — it eliminates the data synchronization
problems, manual handoffs, and reconciliation errors that plague organizations using
separate PM and ERP systems.

**Time tracking with billing** — Built-in timer, manual entry, planned vs. actual
comparison, and direct connection to invoicing. For service companies billing time
and materials, this workflow is tighter than any standalone PM tool can achieve.

**Gantt charts** (v19) — Significantly improved with intelligent zoom (hours through
quarters), sparse mode (hiding empty rows), drag-resize tooltips, and buffer
preservation when rescheduling dependent tasks. The Gantt is now competitive with
mid-tier standalone tools.

**Task hierarchy and dependencies** — Tasks, sub-tasks, checklists, finish-to-start
dependencies visualizable in Gantt. Functional for straightforward project structures.

**Milestones** — Deadline tracking with Gantt diamond icons, color-coded by status.

**Recurring tasks and templates** (v19) — Reusable task templates with stages and
assignees. Useful for standardizing repetitive work.

**Custom property fields** (v16+) — Add project-specific metadata without development.

### 13.2 What Odoo Gets Wrong

**Sub-task architecture is broken.** Sub-tasks can be associated with a completely
different project than their parent — described by forum users as "weird and immensely
confusing." Timesheets cannot be logged directly to parent tasks but aggregate from
children. This creates a hierarchy that does not behave like users expect.

**Project template duplication links back to originals** rather than creating
independent copies. Changes to a template-created project can corrupt the template
and other projects derived from it. This is a data integrity issue, not a UX issue.

**Planning and Project modules are disconnected.** Resource shifts created in Planning
do not reflect as task allocations in Project, and vice versa. This means an
organization cannot see both "who is available" and "what work needs doing" in a
single view — the fundamental requirement for resource management.

**Community verdict (Odoo Forum, April 2024)**: "Odoo project management was almost
completely unusable up to V16. As of V17, it is still a very long way away from
being a complete mature solution."

### 13.3 Feature Gap Summary

Features absent from Odoo core that are supported by Tier 1-3 evidence:

| Feature | Evidence Tier | Available in Core? | Workaround? |
|---------|--------------|-------------------|-------------|
| Flow metrics (cycle time, throughput, WIP, CFD) | T1 | No | None |
| Multi-dimensional success criteria | T1-2 | No | None |
| Risk register with probability/impact | T2 | No | OCA `project_risk` |
| Cross-project resource utilization | T2 | No | None |
| Portfolio dashboard | T2 | Partial (Enterprise) | Limited |
| Project health indicators (automated) | T2-3 | No | None |
| Benefits realization tracking | T2 | No | None |
| Historical data for estimation | T1-2 | No | None |
| Retrospective / action tracking | T2-3 | No | None |
| Budget tracking in-module | T2 | No | OCA `project_budget` |
| Critical path calculation | T3 | No | OCA (outdated) |
| Additional dependency types (SS/FF/SF) | T3 | No | None |
| Lag/lead time on dependencies | T3 | No | Partial (v19 buffer) |
| Sprint / backlog management | T2-3 | No | Third-party app |
| Project baseline (snapshot) | T3 | No | None |
| Kill criteria / gate review | T2-3 | No | None |
| Pre-mortem template | T2 | No | None |

---

## 14. Gap Analysis: Evidence-Based Priorities

### Gap 1: No Flow Metrics [CRITICAL, T1]

This is the highest-confidence, highest-impact gap. Flow metrics are backed by
mathematical theorem (Little's Law), validated by the most rigorous software delivery
research (DORA), and demonstrated in practitioner case studies (Siemens).

**What's needed:**

- **Cycle time calculation**: Automatically computed per task from the timestamp of
  entering the first "active" stage to the timestamp of entering the "done" stage.
  This requires no user input — just stage transition timestamps that Odoo already
  records.

- **Lead time calculation**: From task creation date to task completion date. Again,
  automatic from existing data.

- **Throughput tracking**: Tasks completed per period (week, sprint, month) per
  project. Displayable as a histogram showing throughput distribution over time.

- **WIP visualization**: Current count of tasks in each active stage, displayed on
  the Kanban board. Optional WIP limits per stage (configurable per project) with
  visual warning when exceeded.

- **Cumulative Flow Diagram**: Stacked area chart showing task count per stage over
  time. The single most information-dense visualization in PM — shows flow health,
  bottlenecks, WIP trends, and throughput in one chart.

- **Cycle time scatter plot**: Individual tasks plotted by completion date (x-axis)
  and cycle time (y-axis), with percentile lines (50th, 85th, 95th). Shows
  predictability trends and outlier identification.

**Implementation note**: Most of this data already exists in Odoo's audit trail
(stage transition timestamps on `mail.tracking.value`). The primary effort is
building the visualizations and aggregate computations, not collecting new data.

### Gap 2: No Multi-Dimensional Success Measurement [CRITICAL, T1-2]

Odoo measures task completion. It does not measure whether projects achieve their
intended purpose.

**What's needed:**

- **Success criteria definition at project initiation**: A structured form on the
  project allowing definition of expected benefits (quantified), measurement methods,
  measurement dates, and accountable person. Example: "Reduce customer support call
  volume by 30% within 6 months. Measured via helpdesk ticket count. Accountable:
  Customer Service Director."

- **Post-delivery benefit tracking**: Scheduled reviews at 3, 6, and 12 months after
  project completion, comparing actual outcomes against defined success criteria.

- **Project outcome scoring**: A multi-dimensional rating covering delivery efficiency
  (Iron Triangle), customer impact, team health, and business results — following
  the Shenhar & Dvir model.

- **Organizational learning from outcomes**: Aggregate outcome data across completed
  projects to identify patterns — which types of projects consistently deliver on
  their business cases, which don't, and what factors distinguish them.

### Gap 3: No Risk Management [HIGH, T2]

**What's needed:**

- **Risk register**: Each risk has: description, category (technical/organizational/
  external/financial), probability (1-5), impact (1-5), risk score (probability x
  impact), response strategy (mitigate/transfer/accept/avoid), response plan
  (concrete actions), owner, status, and dates.

- **Risk matrix visualization**: Probability x impact grid with risks plotted as
  points. Color-coded by severity zone (green/yellow/red).

- **Risk trends over time**: Chart showing total risk exposure (sum of risk scores)
  over time. Should decrease as risks are mitigated. Increasing total exposure is
  a warning signal.

- **Pre-mortem template**: Structured project initiation step that prompts team
  members to imagine failure and identify risks. Can be as simple as a rich text
  field with prompts, but having it as a standard project initiation step is the key.

- **Integration with project health**: Risk exposure should feed into the project
  health indicator (Gap 5).

### Gap 4: Cross-Project Resource Visibility [HIGH, T2]

**What's needed:**

- **Resource utilization dashboard**: For each employee, show total allocated hours
  across all active projects vs. available hours. Highlight overallocation (>100%
  utilization) with visual warnings.

- **Planning-Project bridge**: Synchronize resource allocation between the Planning
  module and Project module so that capacity is visible in both contexts.

- **What-if modeling**: Ability to simulate "what happens to project timelines if we
  add/remove resource X?" without committing the change.

- **Portfolio-level WIP**: Show how many active projects exist vs. organizational
  capacity. This is the portfolio equivalent of task-level WIP limits.

### Gap 5: Project Health Indicators [HIGH, T2-3]

**What's needed:**

- **Automated health scoring** based on: schedule deviation (% of tasks overdue),
  budget deviation (actual hours vs. planned), milestone completion rate, risk
  exposure, team workload (average utilization of project members).

- **Traffic light system** that is computed, not self-reported. The PM can override
  the computed status, but must provide a written explanation. This preserves
  management judgment while preventing unconscious (or conscious) green bias.

- **Trend indicators**: Is this project improving, stable, or degrading? Computed
  from health score trajectory over the last N weeks.

- **Staleness detection**: Projects with no activity for N days/weeks should be
  automatically flagged. Zombie projects often die quietly — they stop being updated
  rather than being explicitly cancelled.

### Gap 6: Portfolio Dashboard and Governance [HIGH, T2]

**What's needed:**

- **All-projects view**: Every active project with health indicator, progress
  percentage, resource consumption, risk exposure, and strategic alignment score.

- **Strategic alignment**: A field or tag system for linking projects to strategic
  objectives. Filter portfolio view by strategic objective to see which initiatives
  are funded and which are not.

- **Gate review support**: Configurable review points at project milestones where
  continuation requires explicit approval. Template for gate review criteria (is the
  business case still valid? Are resources sufficient? Should we continue, modify,
  or cancel?).

- **Kill criteria**: Defined at project initiation, evaluated at gates. "If the
  project exceeds 150% of budget OR the key customer withdraws OR the technology
  proves infeasible, the project will be paused for formal review."

### Gap 7: Historical Data for Estimation [HIGH, T1-2]

**What's needed:**

- **Automatic capture**: When a project completes, automatically record: planned
  duration vs. actual, planned hours vs. actual, planned cost vs. actual, number of
  tasks planned vs. delivered, key characteristics (project type, team size, domain).

- **Reference class query**: When creating a new project, ability to find similar
  past projects and see their actual outcomes. "Show me all completed projects
  tagged as 'ERP implementation' with 3-5 team members — what were their actual
  durations and effort?"

- **Estimation calibration**: Side-by-side comparison of estimated vs. actual for
  each completed project, building organizational awareness of systematic estimation
  bias.

### Gap 8: Retrospective and Lessons Learned [MEDIUM, T2-3]

**What's needed:**

- **Retrospective records**: Create a retrospective linked to a project (or sprint,
  if sprints are implemented). Fields: what went well, what didn't, action items.

- **Action item tracking**: Each action has: description, owner, due date, status.
  Actions carry forward to subsequent retrospectives until completed.

- **Follow-through enforcement**: The next retrospective's first section shows
  outstanding action items and their status. Unresolved actions are visible, not
  buried.

- **Cross-project knowledge base**: Completed retrospective actions tagged by
  category (estimation, scope, communication, technical, process). Searchable
  across projects so new teams can learn from past teams' discoveries.

### Gap 9: Additional Dependency Types [MEDIUM, T3]

**What's needed:**

- Finish-to-Start (existing), Start-to-Start, Finish-to-Finish, Start-to-Finish
- Configurable lag/lead time per dependency link
- Visual representation of all dependency types in Gantt view

### Gap 10: Critical Path [MEDIUM, T3]

**What's needed:**

- Critical path calculation algorithm (longest path through the dependency network)
- Visual highlighting of critical-path tasks in Gantt view
- Slack (float) time computation per task
- Warning when a critical-path task is delayed (immediate schedule impact)

---

## 15. Implementation Roadmap

### Design Principles (Derived from Evidence)

1. **Support multiple work styles without mandating one.** Methodology matters less
   than fit-to-context. Do not force Agile or Waterfall. Build features that work
   with Kanban flow, Scrum sprints, traditional milestones, or any combination.

2. **Make flow visible.** Flow metrics have the strongest mathematical and empirical
   foundation. They should be first-class citizens, not hidden behind configuration.

3. **Enable honest status.** Automated health indicators that detect problems without
   requiring human self-reporting. Risk registers visible to stakeholders by default.
   Make transparency the path of least resistance.

4. **Track outcomes, not just outputs.** Benefits realization is the biggest conceptual
   gap. Success is not task completion — it is value delivery.

5. **Support portfolio decisions.** Cross-project visibility, resource utilization,
   and strategic alignment are where the highest organizational value lies.

6. **Make history useful.** Every completed project should automatically improve future
   estimation accuracy. The system should get smarter with use.

7. **Deepen the ERP advantage.** Odoo's unique strength is native ERP integration.
   Features that leverage this (project-to-P&L, resource-to-cost, risk-to-financial-
   impact) create competitive moats no standalone PM tool can cross.

8. **Less is more.** Linear's success (4.6/5 dev satisfaction vs. Jira's 3.2/5) shows
   that opinionated simplicity beats feature bloat. Each feature must solve a problem
   supported by Tier 1-3 evidence, not just match a competitor checkbox.

### Phase 1: Flow and Visibility (Highest Impact, Strongest Evidence)

| Feature | Evidence | Effort | Rationale |
|---------|----------|--------|-----------|
| Flow metrics dashboard | T1 | Medium | Mathematically proven, data already exists |
| Risk register (basic) | T2 | Low-Med | Consistent CSF, simple data model |
| Automated health indicators | T2-3 | Medium | Prevents status theater, uses existing data |
| Cross-project resource view | T2 | Med-High | Makes overcommitment visible |
| Retrospective with action tracking | T2-3 | Low | Low effort, high cultural impact |

### Phase 2: Governance and Measurement

| Feature | Evidence | Effort | Rationale |
|---------|----------|--------|-----------|
| Portfolio dashboard | T2 | High | Highest organizational value layer |
| Benefits realization tracking | T2 | Medium | Biggest conceptual gap |
| Project baseline snapshot | T3 | Medium | Enables planned-vs-actual comparison |
| Historical estimation data | T1-2 | Medium | Reference class forecasting enablement |
| Gate review / kill criteria | T2-3 | Low-Med | Prevents zombie projects |
| Pre-mortem template | T2 | Low | Highest-ROI risk identification technique |

### Phase 3: Advanced Scheduling

| Feature | Evidence | Effort | Rationale |
|---------|----------|--------|-----------|
| SS/FF/SF dependency types | T3 | Medium | Needed for complex project structures |
| Lag/lead time per dependency | T3 | Low | Small extension of existing model |
| Critical path calculation | T3 | High | Complex algorithm, high value for large projects |
| Resource leveling (automatic) | T2-3 | Very High | Most technically demanding feature |

### Phase 4: Agile Extensions (Optional, Context-Dependent)

| Feature | Evidence | Effort | Rationale |
|---------|----------|--------|-----------|
| Sprint management | T2-3 | High | Valuable for Scrum teams, not universal |
| Product backlog with prioritization | T2-3 | Medium | Separation from sprint work |
| Monte Carlo forecasting | T2-3 | Medium | Most sophisticated estimation alternative |
| Story points (optional) | T4 | Low | Weak evidence but high demand |
| Velocity tracking | T4 | Low | Weak evidence but expected with sprints |

---

## Appendix A: The Standish CHAOS Report Credibility Problem

The CHAOS Reports are the most-cited statistics in IT project management and among
the least credible by academic standards. Since they are frequently referenced in
PM discussions, this assessment is important for calibrating expectations.

**What CHAOS claims (2020)**: Agile projects are 3x more likely to succeed than
waterfall (42% vs. 13%). Only 31% of IT projects "succeed."

**Academic critiques (all from peer-reviewed IEEE Software):**

Eveleens & Verhoef (2010) applied Standish definitions to 5,457 real forecasts from
1,211 projects. Found the definitions are: (1) misleading — 10% over budget =
"challenged"; (2) one-sided — only captures overruns; (3) pervert estimation — they
incentivize pessimistic estimates; (4) produce meaningless aggregates — no
size/context control.

Glass (2006): If 84% of projects fail catastrophically, the information economy
could not function. The statistics are implausible.

Jorgensen & Molokken-Ostvold (2006): Definitions of success/challenged/failure are
insufficiently specified. Comparable data produces divergent results.

**Methodological problems**: No peer review, no public data access, US-only sample
claimed as global, inconsistent definitions across years, undisclosed survey
population. The Standish Group sells consulting services — commercial incentive to
dramatize the crisis narrative.

**Recommendation**: Do not cite CHAOS statistics as authoritative. Use the McKinsey-
Oxford data (5,400 projects, academic partner) for quantitative claims. Use CHAOS
only as directional indication that IT delivery has systemic problems — with caveats.

---

## Appendix B: The Agile Industrial Complex

Term coined by Martin Fowler (2018). Core observation: the project management
industry has commercially captured the Agile movement, converting it from a set of
values about human-centered software development into a certification and consulting
revenue stream.

**The commercial machinery:**
- Scrum Alliance: certification ecosystem generating revenue through training partners
- Scrum.org: Ken Schwaber's for-profit certification organization
- Scaled Agile, Inc.: 2M+ certified professionals, $699-$1,650/course, $295/year
  renewal. Acquired by Eurazeo (French private equity)
- The resulting dynamic: consultants recommend the frameworks they are certified to
  deliver. Organizations are sold transformation programs. Success is measured by
  framework adoption, not business outcomes.

**Manifesto signatories' own assessment:**
- Ron Jeffries (2018): "Developers should abandon Agile" — not because agile is
  wrong but because the brand is corrupted beyond recovery
- Dave Thomas (2014): "The word 'agile' has been subverted to the point where it is
  effectively meaningless"
- Martin Fowler (2018): Most implementations are "faux-agile — agile that's just the
  name, but none of the practices and values in place"

**Relevance for Odoo**: Implementing "Agile features" (sprints, story points,
velocity) without the underlying practices (psychological safety, technical
excellence, frequent delivery, team autonomy) reproduces the Agile Industrial
Complex in software form. If Odoo adds Agile features, they should serve the
evidence-backed practices (flow metrics, frequent releases, WIP limits) rather than
the certification-driven rituals (velocity tracking as performance metric, sprint
commitment as deadline).

---

## Appendix C: Bias Assessment Summary

| Source Category | Primary Bias | Mitigation |
|----------------|-------------|------------|
| PMI (Pulse, PMBOK) | Commercial — sells certifications | Cross-reference with independent academic research |
| Standish CHAOS | Commercial — sells consulting; methodological | Do not use as authoritative; prefer McKinsey-Oxford |
| Scrum.org / Scrum Alliance | Commercial — sells certifications | Use ACM peer-reviewed study instead |
| Scaled Agile / SAFe | Commercial — sells certifications and licensing | Note US Air Force rejection; no independent validation |
| Digital.ai State of Agile | Commercial — sells Agile tools; self-selected respondents | Note small sample (350 in 18th report), respondent bias |
| McKinsey / BCG / Gartner | Commercial — sells advisory services | Academic partners add credibility; note selection bias |
| DORA / Google | Institutional — Google-affiliated since 2018 | Longitudinal design, large N, published methodology |
| Academic journals (IJPM, PMJ, ASQ) | Publication — positive results published more | Note effect sizes and replication status |
| Practitioner blogs (Jeffries, Fowler) | Ideological — committed to specific agile vision | Use for qualitative insight, not quantitative claims |
| Kanban University | Commercial — sells certification | Little's Law is mathematically sound independent of vendor |
| Odoo forums | Self-selected dissatisfied users | Corroborate with feature analysis and competitor comparison |
