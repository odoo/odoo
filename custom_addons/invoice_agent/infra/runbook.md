# Invoice Agent — Infrastructure Runbook

The operational record for the AI Invoice Agent's AWS environment. Append to this file every day;
never rewrite history. If a future you is paged at 2am, this is the only file that matters.

- **Product:** Odoo 19 AI Invoice Agent (`invoice_agent` addon)
- **Target launch:** 2026-10-10
- **Started:** 2026-07-15

---

## 1. Account & identity

| Field | Value |
|---|---|
| AWS account ID | _(fill in: top-right of console → Account)_ |
| Account alias | |
| Root email | |
| Root MFA enabled | _(yes/no + method)_ |
| IAM admin username | |
| IAM admin MFA enabled | _(yes/no + method)_ |
| Console sign-in URL | `https://<account-id>.signin.aws.amazon.com/console` |
| CLI profile name | `invoice-agent` |
| `aws sts get-caller-identity` ARN | |

> Root credentials are used **once** — to create the IAM admin user — and then never again.
> Everything after that is the IAM user.

---

## 2. Region

| Field | Value |
|---|---|
| Region | `me-south-1` (Bahrain) |
| AZ (subnet) | |

**Why this region:** nearest mature region to Saudi end users, and it carries every service this
product needs (EC2, EBS gp3, VPC, S3, ECR, CloudWatch, Budgets). See `## Decisions` below.

---

## 3. Network (VPC)

Built **before** the instance — an instance's VPC/subnet cannot be changed after launch.

| Field | Value |
|---|---|
| VPC ID | |
| VPC name tag | `invoice-agent-vpc` |
| VPC CIDR | `10.20.0.0/16` |
| Public subnet ID | |
| Public subnet CIDR | `10.20.1.0/24` |
| Public subnet AZ | |
| Auto-assign public IPv4 | _(enabled/disabled)_ |
| Internet gateway ID | |
| Route table ID | |
| Route: `0.0.0.0/0` → IGW | _(confirm present)_ |

### Security group

| Field | Value |
|---|---|
| SG ID | |
| SG name | `invoice-agent-sg` |

**Inbound rules**

| Port | Protocol | Source | Why |
|---|---|---|---|
| 22 | TCP | `<my-ip>/32` | SSH — my IP only, never `0.0.0.0/0` |
| 80 | TCP | `0.0.0.0/0` | HTTP — ACME/Let's Encrypt challenge + redirect to 443 |
| 443 | TCP | `0.0.0.0/0` | HTTPS — the Odoo web UI |

**Outbound rules**

| Port | Protocol | Destination | Why |
|---|---|---|---|
| All | All | `0.0.0.0/0` | Default allow-all — apt, Docker pulls, Claude API |

> My home IP is dynamic. When SSH suddenly hangs, re-check it:
> `curl -s https://checkip.amazonaws.com` then update the port-22 rule.

---

## 4. Compute (EC2)

| Field | Value |
|---|---|
| Instance ID | |
| Name tag | `invoice-agent-prod` |
| Instance type | `t3.medium` (2 vCPU, 4 GiB) |
| AMI ID | |
| AMI name | Ubuntu Server 24.04 LTS (Noble), amd64 |
| AMI owner | `099720109477` (Canonical) |
| Launched (date) | |
| Key pair name | `invoice-agent` |
| Key file (local) | `D:\.ssh\invoice-agent.pem` |
| Elastic IP | |
| EIP allocation ID | |
| Private IP | |

### The exact SSH command that works

```
ssh -i D:\.ssh\invoice-agent.pem ubuntu@<elastic-ip>
```

> Username is `ubuntu` for Ubuntu AMIs (`ec2-user` on Amazon Linux, `admin` on Debian).
> Getting this wrong looks identical to a key problem — see the troubleshooting table.

### Storage

| Field | Value |
|---|---|
| Root volume ID | |
| Size | 30 GiB |
| Type | gp3 |
| Device | `/dev/nvme0n1` (Nitro) → `/dev/nvme0n1p1` root partition |
| Delete on termination | _(yes/no)_ |

Resize procedure (console resize, then grow the filesystem in-guest — the OS does not notice on its own):

```
lsblk                              # confirm disk is 30G but partition is still 8G
sudo growpart /dev/nvme0n1 1       # grow the PARTITION (note the space before "1")
sudo resize2fs /dev/nvme0n1p1      # grow the FILESYSTEM
df -h /                            # confirm ~30G available
```

### AMI snapshot (rollback point)

| Field | Value |
|---|---|
| AMI ID | |
| AMI name | `invoice-agent-baseline-2026-07-15` |
| Snapshot ID | |
| Taken (date) | |

---

## 5. Cost control

| Field | Value |
|---|---|
| Budget name | `invoice-agent-monthly` |
| Budget amount | $30/month |
| Alert threshold | 80% actual, 100% forecast |
| Alert email | |
| Created (date) | |

**Standing cost (charged even when the instance is STOPPED):**

| Item | Charged while stopped? |
|---|---|
| t3.medium compute | No — stopping stops the meter |
| 30 GB gp3 EBS | **Yes** |
| Elastic IP | **Yes** — public IPv4 has been billed hourly since 2024-02-01, attached or not |

> The $30 budget only holds if the instance is **stopped when not in use**. Left running 24/7,
> compute alone lands near the cap before storage and IP are added. Stop it at the end of each
> study day. Actual verified figures are in `## Decisions`.

---

## 6. Runtime facts (from the box itself)

Recorded after first SSH, so I know the machine's real shape:

```
lsblk      # block devices — is the root volume the size I paid for?
free -h    # memory — t3.medium should show ~3.8Gi
df -h      # filesystem usage — is / actually grown?
uname -a   # kernel + arch
```

| Command | Output summary |
|---|---|
| `lsblk` | |
| `free -h` | |
| `df -h /` | |

---

## 7. SSH troubleshooting log

| Symptom | Cause | Fix |
|---|---|---|
| `Permission denied (publickey)` | Wrong username (`root`/`ec2-user` instead of `ubuntu`) | Use `ubuntu@` |
| `Permission denied (publickey)` | Wrong key, or key not the one baked into the AMI at launch | Confirm key pair name matches the instance's |
| `UNPROTECTED PRIVATE KEY FILE` | `.pem` readable by other Windows users | See the icacls block below |
| Connection **times out** (hangs) | SG port 22 doesn't allow my current IP | `curl -s https://checkip.amazonaws.com`, update SG rule |
| Connection **refused** (fast) | Instance still booting, or sshd down | Wait for 2/2 status checks; check console screenshot |
| Times out after working yesterday | Home IP changed, **or** public IP changed on stop/start | Elastic IP fixes the second; SG rule fixes the first |
| `Host key verification failed` | Rebuilt the box, same IP, old key in known_hosts | `ssh-keygen -R <ip>` |

### Locking down the key on Windows

`chmod 400` is the Linux instruction. Windows has no chmod — the NTFS equivalent is:

```
icacls D:\.ssh\invoice-agent.pem /inheritance:r
icacls D:\.ssh\invoice-agent.pem /grant:r "$env:USERNAME:R"
```

This strips inherited ACLs and grants read to only me, which is what OpenSSH actually checks.

---

## 8. Decisions

Append one entry per decision worth defending later.

### 2026-07-15 — Region: me-south-1 (Bahrain)
_(rationale + verified cost delta — fill in)_

### 2026-07-15 — VPC built before instance launch
An EC2 instance's VPC and subnet are fixed at launch and cannot be changed afterward; moving means
re-launching from an AMI. So the network is built first, and the instance launches into it.

---

## 9. Daily log

### 2026-07-15 — Day 1: AWS foundation
- [ ] Root MFA enabled
- [ ] IAM admin user created, MFA enabled, root credentials retired
- [ ] AWS CLI installed, `aws configure` done
- [ ] `aws sts get-caller-identity` returns the IAM user ARN (not root)
- [ ] VPC + public subnet + IGW + route table built
- [ ] Security group: 22 from my IP, 80 + 443 open
- [ ] t3.medium Ubuntu 24.04 launched into the VPC
- [ ] Elastic IP allocated and associated
- [ ] SSH works with key only
- [ ] `lsblk` / `free -h` / `df -h` recorded above
- [ ] Root volume resized to 30 GB, filesystem grown
- [ ] AMI baseline snapshot taken
- [ ] Budget alarm set at $30/month
- [ ] This runbook committed on `chore/aws-foundation` and pushed

Notes:
-
