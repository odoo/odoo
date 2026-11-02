# AUTO-INFO Ring Variants 50 แบบ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้างภาพสัญลักษณ์ `A` + วงแหวน จำนวน 50 แบบ โดยคง `A` เดิมเป็นพิมพ์เขียว และเปลี่ยนเฉพาะวงแหวนตามโครง 5 families x 10 แบบ

**Architecture:** งานนี้แบ่งเป็น 4 ชั้น: (1) เตรียม reference และ blueprint ของ `A`, (2) สร้าง prompt matrix ราย family และรายแบบ, (3) generate ภาพจริงแบบ batch ที่ควบคุมชื่อไฟล์และความต่างของวงแหวน, (4) สรุปผลด้วย gallery และ scorecard เพื่อให้คัดตัวเด่นได้เร็ว โดยไม่ย้อนกลับไปตีความโจทย์ใหม่ทุกครั้ง

**Tech Stack:** Local workspace files, Markdown manifests, PNG assets, HTML gallery, `GenerateImage` แบบ image-to-image, PowerShell สำหรับจัดโฟลเดอร์/ตรวจไฟล์

---

## โครงสร้างไฟล์ที่จะใช้

- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\reference\auto-info-source.png`
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\reference\auto-info-symbol-blueprint.png`
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\family-briefs.md`
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\prompt-matrix.md`
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\generation-log.csv`
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\review-scorecard.csv`
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\A01-crystal-orbit.png` ถึง `E10-hybrid-signature.png`
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\gallery\index.html`
- Reference: `c:\odoo-dev\odoo19\docs\superpowers\specs\2026-11-02-auto-info-ring-variants-design.md`
- Reference: `c:\odoo-dev\odoo19\docs\superpowers\plans\2026-11-02-auto-info-ring-variants-implementation-plan.md`

---

### Task 1: จัดเตรียม reference และ blueprint ของตัว A

**Files:**
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\reference\auto-info-source.png`
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\reference\auto-info-symbol-blueprint.png`
- Modify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\generation-log.csv`

- [ ] **Step 1: สร้างโฟลเดอร์ deliverable**

Run:

```powershell
New-Item -ItemType Directory -Force "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\reference" | Out-Null
New-Item -ItemType Directory -Force "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests" | Out-Null
New-Item -ItemType Directory -Force "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images" | Out-Null
New-Item -ItemType Directory -Force "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\gallery" | Out-Null
```

Expected: สร้าง 4 โฟลเดอร์สำเร็จโดยไม่มี error

- [ ] **Step 2: บันทึกภาพต้นฉบับจากไฟล์แนบเป็น `auto-info-source.png`**

ผลลัพธ์ไฟล์เป้าหมาย:

```text
c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\reference\auto-info-source.png
```

เงื่อนไข:
- ใช้ภาพแนบที่ผู้ใช้ส่งเป็น source of truth
- ห้ามปรับสี ห้าม retouch ห้ามเปลี่ยน composition ของภาพต้นฉบับในขั้นนี้

- [ ] **Step 3: สร้าง `auto-info-symbol-blueprint.png` เป็นภาพอ้างอิงเฉพาะสัญลักษณ์**

ข้อกำหนดของไฟล์:

```text
- ครอบเฉพาะตัว A และวงแหวนเดิม
- ตัดส่วนข้อความ AUTO-INFO, tagline, และเส้นสีด้านล่างออก
- รักษาสัดส่วนและมุมมองเดิม
- พื้นหลังสะอาด พร้อมใช้เป็นภาพอ้างอิงสำหรับ image-to-image
```

- [ ] **Step 4: สร้าง generation log ไฟล์ตั้งต้น**

สร้างไฟล์ `generation-log.csv` ด้วยเนื้อหานี้:

```csv
file_name,family,variant_code,ring_theme,trajectory,mass,material,energy,status,notes
```

- [ ] **Step 5: ตรวจว่าไฟล์อ้างอิงพร้อมใช้**

Run:

```powershell
Get-Item "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\reference\auto-info-source.png","c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\reference\auto-info-symbol-blueprint.png" | Select-Object FullName,Length
```

Expected: ต้องเห็นไฟล์ 2 รายการและ `Length` มากกว่า 0

---

### Task 2: แตก family briefs และกฎความต่างให้ครบ 50 แบบ

**Files:**
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\family-briefs.md`
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\prompt-matrix.md`

- [ ] **Step 1: เขียน family briefs ทั้ง 5 กลุ่ม**

สร้าง `family-briefs.md` ด้วยโครงนี้:

```md
# AUTO-INFO Ring Families

## Family A — Crystal Orbit
- Core mood: crystal, premium, light, precise
- Ring priority: transparency > reflection > speed
- Avoid: thick heavy ring, aggressive flame trail

## Family B — Chrome Velocity
- Core mood: chrome, speed, machine, sharp
- Ring priority: metallic edge > forward motion > power
- Avoid: soft halo, overly delicate transparency

## Family C — Premium Halo
- Core mood: luxury, balance, corporate, stable
- Ring priority: elegant sweep > controlled highlights > readability
- Avoid: chaotic plasma glow, extreme distortion

## Family D — Tech Plasma Ring
- Core mood: futuristic, luminous, high-tech, energetic
- Ring priority: glow edge > semi-transparent energy > advanced look
- Avoid: muddy chrome, overly flat ring surface

## Family E — Hybrid Signature
- Core mood: balanced premium + aggressive + futuristic
- Ring priority: brand hero quality > signature silhouette > mixed material
- Avoid: similarity to Family A-D without a defining twist
```

- [ ] **Step 2: เขียน prompt matrix 50 รายการ**

สร้าง `prompt-matrix.md` ให้ใช้ template นี้กับทุกแบบ:

```md
# AUTO-INFO Prompt Matrix

## Global prompt rules
- Keep the original A structure unchanged as the blueprint.
- Redesign only the orbital ring around the A.
- Symbol only, no text, no tagline.
- Main palette: vivid red, silver chrome, transparent glass.
- Premium 3D logo rendering, clean background, centered composition.
- Preserve brand recognizability and keep the A dominant.

## A01
- File: A01-crystal-orbit.png
- Ring theme: thin crystal sweep with silver edge
- Differentiators: high transparency, upper-right flare, soft front crossing

## A02
- File: A02-crystal-orbit.png
- Ring theme: double-layer glass ring with red core
- Differentiators: medium transparency, rear orbit emphasis, sharper exit
```

ข้อกำหนด:
- ต้องมีรายการครบ `A01-A10`, `B01-B10`, `C01-C10`, `D01-D10`, `E01-E10`
- แต่ละรายการต้องระบุอย่างน้อย 3 differentiators
- แต่ละรายการต้องต่างจากรายการก่อนหน้าอย่างน้อย 2 ปัจจัย

- [ ] **Step 3: เติม differentiators ให้ครบทุก family**

ใช้ชุดคำควบคุมนี้กระจายสลับกัน:

```text
trajectory: shallow / medium / steep / forward slash / rear-biased / centered wrap
mass: ultra-thin / thin / medium / medium-heavy
material: crystal / chrome / red-glass / mixed chrome-glass / plasma-glass
energy: calm / balanced / fast / aggressive / luminous
```

- [ ] **Step 4: ตรวจความครบของ prompt matrix**

Run:

```powershell
rg -n "^## [A-E][0-9]{2}$" "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\prompt-matrix.md"
```

Expected: พบทั้งหมด 50 รายการ

---

### Task 3: สร้าง prompt master สำหรับ image-to-image

**Files:**
- Modify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\prompt-matrix.md`

- [ ] **Step 1: เพิ่ม global master prompt ที่ใช้ร่วมกัน**

เพิ่มบล็อกนี้ไว้ต้นไฟล์:

```md
### Master Prompt
Use the provided AUTO-INFO symbol image as the reference blueprint. Keep the original red 3D A letterform unchanged in structure, proportion, angle, and dominance. Redesign only the orbital ring. Create a premium symbol-only logo with no words. Use vivid red, silver chrome, and transparent glass-like material. The ring may change in trajectory, thickness, material, and energy, but it must still feel like part of one brand family. Clean light background, centered composition, polished reflections, strong readability, high-end industrial automation identity.
```

- [ ] **Step 2: เพิ่ม negative prompt rules สำหรับทุกแบบ**

เพิ่มบล็อกนี้:

```md
### Negative Rules
- Do not change the shape of the A.
- Do not add text, taglines, badges, shields, gears, or extra icons.
- Do not turn the logo into a poster scene.
- Do not overfill the composition with smoke, sparks, or abstract background effects.
- Do not hide the A behind the ring.
```

- [ ] **Step 3: เตรียม format prompt รายภาพ**

ใช้ format นี้กับทุก variant:

```md
Prompt Format:
[Master Prompt]
Variant focus: [ring theme].
Trajectory: [trajectory].
Mass: [mass].
Material: [material].
Energy: [energy].
Differentiators: [differentiator 1], [differentiator 2], [differentiator 3].
[Negative Rules]
```

- [ ] **Step 4: ตรวจว่าไม่มี placeholder**

Run:

```powershell
rg -n "TODO|TBD|similar to|fill in" "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\prompt-matrix.md"
```

Expected: ไม่พบผลลัพธ์

---

### Task 4: Generate Family A — Crystal Orbit จำนวน 10 แบบ

**Files:**
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\A01-crystal-orbit.png` ถึง `A10-crystal-orbit.png`
- Modify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\generation-log.csv`

- [ ] **Step 1: ใช้ `auto-info-symbol-blueprint.png` เป็นภาพอ้างอิง**

Reference image:

```text
c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\reference\auto-info-symbol-blueprint.png
```

- [ ] **Step 2: Generate A01-A05**

สำหรับแต่ละไฟล์:
- ใช้ master prompt + variant prompt ของ family A
- ส่งออกเป็น PNG
- เก็บชื่อไฟล์ให้ตรง matrix

สถานะที่ต้องบันทึกลง `generation-log.csv`:

```csv
A01-crystal-orbit.png,A,A01,thin crystal sweep with silver edge,medium,thin,crystal,balanced,generated,
```

- [ ] **Step 3: Generate A06-A10**

เงื่อนไขเพิ่มเติม:
- อย่างน้อย 3 แบบต้องเน้น transparency เป็นพระเอก
- อย่างน้อย 3 แบบต้องเน้น reflection edge แบบแก้ว
- อย่างน้อย 2 แบบต้องมี front crossing ต่างจาก A01-A05 อย่างชัดเจน

- [ ] **Step 4: ตรวจไฟล์ Family A**

Run:

```powershell
Get-ChildItem "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\A*.png" | Measure-Object
```

Expected: `Count : 10`

---

### Task 5: Generate Family B — Chrome Velocity จำนวน 10 แบบ

**Files:**
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\B01-chrome-velocity.png` ถึง `B10-chrome-velocity.png`
- Modify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\generation-log.csv`

- [ ] **Step 1: Generate B01-B05 โดยเน้น chrome + speed**

กฎ:

```text
- silver chrome ต้องเด่นกว่า transparency
- trajectory ต้องพุ่งแรงกว่า family A
- ห้ามทำให้ ring กลายเป็นใบมีดจนแข็งเกินแบรนด์
```

- [ ] **Step 2: Generate B06-B10 โดยกระจายมุมและน้ำหนัก**

กฎ:

```text
- อย่างน้อย 2 แบบเป็น rear-biased orbit
- อย่างน้อย 2 แบบเป็น forward slash orbit
- อย่างน้อย 2 แบบใช้ medium-heavy ring
```

- [ ] **Step 3: ตรวจไฟล์ Family B**

Run:

```powershell
Get-ChildItem "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\B*.png" | Measure-Object
```

Expected: `Count : 10`

---

### Task 6: Generate Family C — Premium Halo จำนวน 10 แบบ

**Files:**
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\C01-premium-halo.png` ถึง `C10-premium-halo.png`
- Modify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\generation-log.csv`

- [ ] **Step 1: Generate C01-C05 โดยเน้น elegance**

กฎ:

```text
- ring sweep ต้องเรียบและอ่านง่าย
- highlight ต้องหรู ไม่แหลมดุ
- transparency ใช้เพื่อยกระดับ premium ไม่ใช่เพื่อความ sci-fi
```

- [ ] **Step 2: Generate C06-C10 โดยคุม corporate balance**

กฎ:

```text
- ทุกแบบต้องอ่านชัดในขนาดย่อ
- หลีกเลี่ยง trail ยาวเกินจำเป็น
- ใช้ chrome และ glass อย่างสมดุล
```

- [ ] **Step 3: ตรวจไฟล์ Family C**

Run:

```powershell
Get-ChildItem "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\C*.png" | Measure-Object
```

Expected: `Count : 10`

---

### Task 7: Generate Family D — Tech Plasma Ring จำนวน 10 แบบ

**Files:**
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\D01-tech-plasma-ring.png` ถึง `D10-tech-plasma-ring.png`
- Modify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\generation-log.csv`

- [ ] **Step 1: Generate D01-D05 โดยเน้น luminous tech look**

กฎ:

```text
- ต้องมี edge lighting หรือ glow แบบควบคุมได้
- ห้ามทำฉากหลังมืดหรือ cinematic เกินไป
- ring ต้องยังดูเป็นวัสดุของโลโก้ ไม่ใช่สายฟ้าลอย
```

- [ ] **Step 2: Generate D06-D10 โดยเพิ่มพลังและความต่าง**

กฎ:

```text
- อย่างน้อย 2 แบบใช้ plasma-glass material
- อย่างน้อย 2 แบบใช้ steep orbit
- อย่างน้อย 2 แบบใช้ luminous energy สูง แต่ยังไม่กลบ A
```

- [ ] **Step 3: ตรวจไฟล์ Family D**

Run:

```powershell
Get-ChildItem "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\D*.png" | Measure-Object
```

Expected: `Count : 10`

---

### Task 8: Generate Family E — Hybrid Signature จำนวน 10 แบบ

**Files:**
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\E01-hybrid-signature.png` ถึง `E10-hybrid-signature.png`
- Modify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\generation-log.csv`

- [ ] **Step 1: Generate E01-E05 เป็นกลุ่ม hero candidates**

กฎ:

```text
- ผสม premium + aggressive + futuristic ในภาพเดียว
- ต้องมี signature silhouette ที่จำง่าย
- ทุกแบบต้องเหมาะเป็นตัวเต็งแบรนด์หลัก
```

- [ ] **Step 2: Generate E06-E10 เป็นกลุ่ม contrast heroes**

กฎ:

```text
- ต่างจาก E01-E05 อย่างน้อย 2 ปัจจัย
- มีทั้งแบบเบาใสและแบบหนักแน่น
- รักษา red / silver / glass เป็นแกนเสมอ
```

- [ ] **Step 3: ตรวจไฟล์ Family E**

Run:

```powershell
Get-ChildItem "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\E*.png" | Measure-Object
```

Expected: `Count : 10`

---

### Task 9: สร้าง review scorecard และประเมิน 50 แบบ

**Files:**
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\review-scorecard.csv`
- Modify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\generation-log.csv`

- [ ] **Step 1: สร้าง scorecard template**

สร้าง `review-scorecard.csv` ด้วยเนื้อหานี้:

```csv
file_name,family,brand_fidelity,ring_distinction,premium_feel,motion_automation,scalability,hero_potential,total_score,shortlist,notes
```

- [ ] **Step 2: ประเมินทุกไฟล์ A01-E10**

เกณฑ์คะแนน:

```text
1-5 ต่อหัวข้อ
total_score = ผลรวม 6 หัวข้อ (เต็ม 30)
shortlist = yes เมื่อ total_score >= 24
```

- [ ] **Step 3: ทำ shortlist ขั้นแรก**

เป้าหมาย shortlist:

```text
- เลือกประมาณ 8-12 แบบ
- ต้องมีอย่างน้อย 1 แบบจากทุก family
- ถ้า family ใดคะแนนต่ำทั้งหมด ให้เก็บตัวสูงสุดของ family นั้นไว้ 1 แบบ
```

- [ ] **Step 4: ตรวจว่ากรอกครบ 50 แถว**

Run:

```powershell
(Get-Content "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\review-scorecard.csv").Count
```

Expected: อย่างน้อย 51 บรรทัดรวม header

---

### Task 10: สร้าง HTML gallery สำหรับดู 50 แบบและ shortlist

**Files:**
- Create: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\gallery\index.html`

- [ ] **Step 1: สร้าง gallery HTML**

ใช้โครงนี้:

```html
<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="utf-8" />
  <title>AUTO-INFO Ring Variants</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #f4f5f7; color: #222; }
    h1 { margin-bottom: 8px; }
    .family { margin-top: 32px; }
    .grid { display: grid; grid-template-columns: repeat(5, minmax(180px, 1fr)); gap: 16px; }
    .card { background: #fff; border-radius: 12px; padding: 12px; box-shadow: 0 2px 10px rgba(0,0,0,.08); }
    .card img { width: 100%; height: auto; display: block; background: #fff; border-radius: 8px; }
    .name { margin-top: 8px; font-weight: 700; }
    .meta { font-size: 12px; color: #666; }
  </style>
</head>
<body>
  <h1>AUTO-INFO Ring Variants</h1>
  <p>ชุดเปรียบเทียบ 50 แบบ แบ่งตาม 5 families</p>
</body>
</html>
```

- [ ] **Step 2: เติม section แยก Family A-E**

แต่ละ family ใช้ pattern นี้:

```html
<section class="family">
  <h2>Family A — Crystal Orbit</h2>
  <div class="grid">
    <div class="card">
      <img src="../images/A01-crystal-orbit.png" alt="A01-crystal-orbit" />
      <div class="name">A01-crystal-orbit</div>
      <div class="meta">Crystal Orbit</div>
    </div>
  </div>
</section>
```

- [ ] **Step 3: เปิดไฟล์ HTML เพื่อตรวจสายตา**

Run:

```powershell
Start-Process "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\gallery\index.html"
```

Expected: เปิดหน้า gallery ได้ และมองเห็นภาพครบ 50 รายการ

---

### Task 11: ตรวจครบทุก deliverable ก่อนส่งมอบ

**Files:**
- Verify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\reference\*`
- Verify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\*`
- Verify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\*`
- Verify: `c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\gallery\index.html`

- [ ] **Step 1: ตรวจนับภาพทั้งหมด**

Run:

```powershell
Get-ChildItem "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\*.png" | Measure-Object
```

Expected: `Count : 50`

- [ ] **Step 2: ตรวจ manifest files**

Run:

```powershell
Get-Item "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\family-briefs.md","c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\prompt-matrix.md","c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\generation-log.csv","c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\manifests\review-scorecard.csv" | Select-Object Name,Length
```

Expected: ทุกไฟล์มีขนาดมากกว่า 0

- [ ] **Step 3: ตรวจชื่อไฟล์ตาม pattern**

Run:

```powershell
Get-ChildItem "c:\odoo-dev\odoo19\deliverables\auto-info-ring-variants\images\*.png" | Select-Object -ExpandProperty Name
```

Expected: ชื่อไฟล์ครอบคลุม `A01-A10`, `B01-B10`, `C01-C10`, `D01-D10`, `E01-E10`

- [ ] **Step 4: เตรียมสรุปส่งมอบ**

ข้อความสรุปต้องมี:

```text
- จำนวนภาพทั้งหมด 50 แบบ
- shortlist ที่แนะนำ 8-12 แบบ
- family ที่เด่นที่สุด
- ข้อสังเกตเรื่องแนวที่ควร refinement ต่อ
```

---

## การทบทวนแผน (Plan Self-Review)

### 1. Spec coverage

- ข้อกำหนด “คง A เดิม” → Task 1, 3, 4-8
- ข้อกำหนด “ปรับเฉพาะวงแหวน” → Task 2, 3, 4-8
- ข้อกำหนด “50 ภาพจริง” → Task 4-8, 11
- ข้อกำหนด “5 families x 10 แบบ” → Task 2, 4-8
- ข้อกำหนด “คัดตัวเด่น” → Task 9, 10, 11

### 2. Placeholder scan

แผนนี้ไม่มี `TODO`, `TBD`, หรือข้อความประเภท “ทำต่อภายหลัง”

### 3. Type consistency

- ชื่อไฟล์ใช้ระบบเดียวกันทั้งแผน
- family codes A-E สอดคล้องตั้งแต่ matrix ถึง deliverables
- manifests และ gallery ใช้ path เดียวกันตลอด

สรุป: แผนพร้อมสำหรับการเลือกวิธี execution
