# Tax Calculator for Greek Freelancers (2026)
**Υπολογιστής Φόρων για Έλληνες Ελεύθερους Επαγγελματίες**

A single-file web calculator for computing net income, income tax, and advance tax (προκαταβολή φόρου) for Greek freelancers under the 2026 tax regime.

> ⚠️ **Disclaimer**: This is *not* tax advice. It implements the rules as documented in public sources; Greek tax law is complex and changes annually. Always confirm with a licensed accountant (λογιστής) before making decisions.

---

## What it does

- **Multiple income streams** — different clients/locations, different hourly rates, different volumes
- **Itemized expenses with VAT (ΦΠΑ)** — gross input, automatic net-deductible calculation
- **e-EFKA contribution selector** — official 2026 categories (special category for first 5 years + regular 1–6)
- **Progressive income tax** — with new-freelancer discounts auto-applied for years 1–3
- **Advance tax (προκαταβολή φόρου)** — 55% standard / 27.5% for first 3 years
- **Yearly + monthly net** displayed side-by-side
- **Persists across reloads** via `localStorage` (browser-local only — nothing is sent anywhere)

---

## Running it

### Locally
Open `index.html` in any modern browser. No build step, no dependencies, no server.

```bash
open index.html
```

### Hosted
GitHub Pages enables automatic deployment from `main`. After enabling Pages on the repo settings, the calculator becomes available at:

```
https://kostastsi.github.io/tax-calculator/
```

---

## How the math works

### 1. Gross income
Sum across all income streams: `Σ (rate × hours)` per stream.

### 2. Deductible expenses
For each expense row:
```
net_deductible = gross_amount_paid / (1 + vat_rate / 100)
```
This handles the case where you pay 50€ to your accountant *including* 24% VAT — only 40,32€ is income-tax-deductible (the VAT portion is recovered separately via VAT returns if you're VAT-registered, or simply not deductible if you aren't).

### 3. Mandatory contributions (e-EFKA)
2026 monthly amounts (base + 10€ OAED unemployment fund):

| Category | Total monthly |
|---|---|
| Ειδική (πρώτα 5 έτη) | 160,46 € |
| 1η | 260,77 € |
| 2η | 310,93 € |
| 3η | 370,63 € |
| 4η | 443,47 € |
| 5η | 529,45 € |
| 6η | 685,87 € |
| Προσαρμοσμένο | (manual) |

### 4. Taxable income
```
taxable = max(0, gross_income − yearly_other_expenses − yearly_efka)
```

### 5. Progressive income tax (2026)
Applied bracket-by-bracket — each rate hits *only the slice* of income falling inside that bracket.

| Income slice | Rate | New freelancer (years 1–3) |
|---|---|---|
| 0 – 10.000 € | 9% | **4.5%** |
| 10.001 – 20.000 € | 22% | 22% |
| 20.001 – 30.000 € | 28% | 28% |
| 30.001 – 40.000 € | 36% | 36% |
| 40.001 € + | 44% | 44% |

### 6. Advance tax (προκαταβολή φόρου)
```
prokatavoli = tax × (years_active <= 3 ? 0.275 : 0.55)
```

### 7. Net result
```
net_yearly  = taxable − tax
net_monthly = net_yearly / 12
total_due   = tax + prokatavoli
```

---

## What it does NOT model (yet)

- **Τεκμαρτό εισόδημα (presumed minimum income)** — for years 4+, the law imposes a floor based on minimum wage, payroll, and industry turnover. Not modeled because most users in the new-freelancer window (years 1–3) are exempt.
- **Supplementary insurance & lump-sum benefits (επικουρικό + εφάπαξ)** — separate optional EFKA categories.
- **Earned income from employment + freelance** — salary income has its own bracket.
- **Multi-year history / what-if comparisons.**

PRs to add any of the above are welcome.

---

## References

Primary sources used to derive the rules:

- **e-EFKA — Νέοι επαγγελματίες (insurance contribution categories, 2026)**
  https://www.e-efka.gov.gr/el/asphalismenoi/me-misthotoi/neo-systhma-asfalistikon-eisforon/neoi-epaggelmaties

- **ΑΑΔΕ — Προκαταβολή φόρου εισοδήματος από επιχειρηματική δραστηριότητα**
  https://www.aade.gr/

- **Φορολογία ατομικών επιχειρήσεων 2026 — κλίμακα φόρου, εκπτώσεις νέων επαγγελματιών** — informational article cited in development:
  https://www.pkpike.gr/

- **Tekmirio system explanation** (not yet modeled, but documented for future contributors):
  https://www.mysolon.gr/

When the law changes, update:
- `BRACKETS` array (tax brackets)
- `NEW_FREELANCER_FIRST_BRACKET_RATE` (currently 0.045)
- `EFKA_CATEGORIES_2026` array (annual EFKA amounts)
- `calculateProkatavoli` (if rates change)

All four live in the `<script>` block of `index.html`, clearly labeled.

---

## Contributing

PRs welcome, especially for:
- **Annual EFKA value updates** — usually published late January / early February each year
- **Bug fixes** for edge cases (negative income, zero hours, very high incomes 100k+)
- **Translations** — English, German, etc. for international Greek freelancers
- **Tekmirio modeling** for years 4+

### How to test
1. Open `index.html` in a browser.
2. The `calculateTax` JSDoc lists reference values:
   - `calculateTax(10000, 5)` → `900,00 €`
   - `calculateTax(17700.48, 5)` → `2.594,11 €`
   - `calculateTax(17700.48, 1)` → `2.144,11 €`
   - `calculateTax(50000, 5)` → `11.500,00 €`
3. Set up income/expenses to make the taxable income match each row, and verify the displayed tax matches.

### How to submit
1. Fork the repo
2. Make your change in a branch
3. Open a PR with: what changed, what source you cited, manual verification result

---

## License

MIT — see [`LICENSE`](./LICENSE).
