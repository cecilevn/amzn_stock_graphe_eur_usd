# AMZN en dollar et en euro — cahier des charges

Monter un dépôt GitHub qui régénère chaque jour de bourse un graphique du cours d'Amazon
depuis son introduction (15 mai 1997), en dollars et converti en euros au taux du jour,
et le publie sur GitHub Pages.

## Fichiers fournis

- `amzn_stock_history.csv` — historique fusionné, 7 348 séances du 1997-05-15 au 2026-07-31.
- `amzn_stock_template.html` — le graphique, avec le marqueur `__DATA__` à remplacer par le JSON des séries.

Ces deux fichiers sont le point de départ. Les renommer librement dans le dépôt
(`data/history.csv` et `template.html` par exemple), mais conserver leur contenu.

## Règle non négociable

**Le script complète `history.csv`, il ne le régénère jamais.**

Les lignes antérieures au 1999-01-01 utilisent le taux écu/dollar, transcrit depuis une page
d'archive de la Réserve fédérale qui n'est plus maintenue depuis 1999 et dont le `robots.txt`
bloque la récupération automatique. Si le script réécrit le fichier à partir des sources
en ligne, ce segment disparaît définitivement.

Concrètement : lire le CSV existant, déterminer la dernière date présente, ne récupérer que
les séances postérieures, les ajouter en fin de fichier. Ne jamais réécrire ni recalculer
les lignes existantes. Un test doit vérifier qu'après exécution, la première ligne est
toujours `1997-05-15` et que le nombre de lignes n'a jamais diminué.

## Format de `history.csv`

```
date,close_usd,eur_per_usd,close_eur,fx_source
1997-05-15,0.097917,0.871080,0.085294,fed_h10_ecu
```

- `date` — ISO, une ligne par séance du Nasdaq, ordre chronologique croissant
- `close_usd` — clôture ajustée des divisions du titre
- `eur_per_usd` — euros par dollar (≈ 0,87 aujourd'hui). Avant 1999 : inverse du taux dollar/écu.
- `close_eur` — `close_usd * eur_per_usd`
- `fx_source` — provenance du taux : `fed_h10_ecu`, `fed_h10_eur`, `ecb` pour les lignes nouvelles

## Sources

**Cours.** Source principale : Stooq, `https://stooq.com/q/d/l/?s=amzn.us&i=d`, CSV complet,
sans clé ni quota, conditions permissives. Fallback : `yfinance` (API Yahoo non documentée,
qui casse une à deux fois par an — d'où le fallback plutôt que l'inverse).

**Change.** Banque centrale européenne, `eurofxref-hist.csv` : EUR/USD quotidien officiel
depuis 1999, un seul fichier, ni clé ni quota. Attention, la BCE publie des **dollars par euro**
(≈ 1,14) : il faut l'inverser pour obtenir la colonne `eur_per_usd`. Marquer ces lignes `ecb`.

Le passage de la Fed à la BCE pour les nouvelles lignes est volontaire : la BCE est la
référence naturelle vue de France et publie plus tôt. La légère discontinuité méthodologique
avec l'historique Fed est sans effet visible (écart de l'ordre de quelques points de base
sur un même jour) et la colonne `fx_source` la documente.

## Alignement des calendriers

Le Nasdaq et le calendrier de publication BCE ne coïncident pas exactement (Thanksgiving,
Vendredi saint, jours fériés européens). Règle : pour chaque séance de bourse, utiliser le
taux du jour s'il existe, sinon le dernier taux connu (report en avant). Ne jamais interpoler,
ne jamais sauter une séance de bourse faute de taux.

## Workflow

Cron du mardi au samedi vers 23h00 UTC, après la clôture de New York. Le cron GitHub est en
UTC : le décalage avec Paris change d'une heure entre été et hiver, c'est acceptable ici.
Prévoir aussi un déclenchement manuel (`workflow_dispatch`).

Étapes : récupérer les séances manquantes → les ajouter à `history.csv` → injecter le JSON
dans le template → écrire `index.html` → commiter si le contenu a changé → publier sur Pages.

**Alerte de fraîcheur.** Si `history.csv` n'a pas gagné de ligne depuis 5 jours ouvrés,
faire échouer le job avec un message explicite. Sans cela, une panne de source fige le
graphe en silence.

**Workflows planifiés désactivés après 60 jours.** GitHub coupe les workflows `schedule`
après 60 jours sans activité du dépôt, et les commits poussés par le bot Actions avec le
`GITHUB_TOKEN` par défaut ne comptent généralement pas comme activité. Utiliser un token
personnel (PAT à portée réduite, en secret de dépôt) pour les commits automatiques, de
sorte qu'ils comptent comme activité. Documenter ce point dans le README, avec la parade
de repli : un commit manuel occasionnel.

## Publication

Dépôt **public** — publier des Pages depuis un dépôt privé exige GitHub Enterprise Cloud,
et les Actions sont sans plafond de minutes sur les dépôts publics. Aucune donnée
personnelle ne transite ici.

**URL souhaitée : dépôt nommé d'après le projet, pas `<pseudo>.github.io`.**
Le site doit donc être servi à `https://<pseudo>.github.io/<nom-du-depot>/` — par exemple
`amzn-eur`. La racine `<pseudo>.github.io` reste libre pour d'autres usages.

## Rendu

Le template est autonome : pas de dépendance externe, tout est en Canvas. Remplacer `__DATA__`
par un JSON compact de la forme :

```json
{"base":"1997-05-15","t":[0,1,4,...],"usd":[...],"eur":[...],"fx":[...]}
```

- `base` — date de la première séance
- `t` — jours écoulés depuis `base`, un entier par séance
- `usd`, `eur` — cours, 6 chiffres significatifs
- `fx` — **dollars par euro** (l'inverse de la colonne `eur_per_usd` du CSV), 5 chiffres
  significatifs, c'est ce qu'affiche la bande de change en bas du graphique

Mettre à jour dans le template la mention de période en haut de page (« 15 mai 1997 →
31 juillet 2026 · 7 348 séances ») et la note de bas de page sur le report du dernier taux
connu, dont les dates sont aujourd'hui codées en dur.

## README

Y consigner : les sources et leurs conditions, la règle du fichier historique jamais
régénéré, la manœuvre en cas de panne d'une source, et le point sur les 60 jours.
