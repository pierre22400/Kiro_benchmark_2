# Validation du SpecBlock EARS

## Source validée

- Source normative : `specblock` au commit `c3a9c34885f07efb10aa44ce6e1658abe60d8140` (« Revise SpecBlock to version 3 for Evidence Timeline CLI »).
- Fichier de travail : `specblock`.
- Résultat d’intégrité : le fichier est exactement identique à la source Git (`git diff --exit-code c3a9c34885f07efb10aa44ce6e1658abe60d8140 -- specblock` sans sortie) et son JSON est syntaxiquement valide avec Python 3.11.15.

## Cohérence EARS validée

Le SpecBlock v3 définit sans lacune publique connue :

1. **Surface CLI** — les quatre commandes exactes, toutes les options autorisées, leurs valeurs/défauts, l’interdiction des abréviations, les erreurs d’usage et les aides stables.
2. **Données d’entrée** — l’objet `Event` fermé, ses champs et types, les sévérités et rangs, les timestamps RFC3339 acceptés et normalisés, les règles JSONL UTF-8, les lignes physiques et l’unicité globale de `event_id`.
3. **Validation** — les quatre codes `RecordError`, les payloads de validation exacts, les compteurs, l’ordre, ainsi que les comportements distincts de `validate`, `summarize` et `explain` devant une entrée invalide.
4. **Domaine et filtres** — `EventView`, l’ordre déterministe, les filtres `summarize` par AND, les résumés de cas, le contexte exact de `explain` et les payloads associés.
5. **Rendu** — les formats texte et JSON canoniques, le schéma exposé, la règle de nouvelle ligne et les contraintes de déterminisme.
6. **Rédaction** — portée texte, séquence des remplacements et expressions régulières exactes.
7. **E/S et erreurs** — stdin, cibles de sortie, créations de parents, refus des liens symboliques, remplacement atomique, erreurs publiques et leur préséance.
8. **Architecture** — séparation CLI, normalisation de requête, parsing, validation, filtrage, timeline, rédaction, rendu et écriture ; contrats d’interface obligatoires avant la génération de tâches ou de code.

Les six ambiguïtés consignées dans la précédente validation v2 sont résolues par cette révision. Il est donc permis de produire, dans l’ordre, `requirements.md`, `design.md` et `tasks.md`. Aucun code ne sera généré avant leur validation et leurs checkpoints Git respectifs.
