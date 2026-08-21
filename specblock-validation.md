# Validation du SpecBlock EARS

## Source validée

- Source normative demandée : `specblock` au commit `029ee68bdc1087e0186ec2f75d87751f73f7f40c`.
- Fichier de travail : `specblock`.
- Résultat : le fichier de travail est identique au blob source `9b8c5f1e1072fda9288fdafebc361271868e4686`.
- Aucune implémentation ni aucun artefact de spécification (`requirements.md`, `design.md`, `tasks.md`) n’existait lors de cette validation.

## Exigences EARS reconnues

Le SpecBlock impose un CLI local Python, one-shot, fondé sur la bibliothèque standard, sans réseau, serveur, persistance, cache, configuration globale, plugin ou effets à l’import. Il doit proposer `validate`, `summarize`, `explain` et `schema`, lire des événements JSONL, valider, filtrer, trier, construire une timeline par `case_id`, pouvoir rédiger la sortie humaine et rendre du texte ou du JSON de façon déterministe.

La spécification exige aussi des contrats stricts pour l’aide, les flux stdout/stderr, les codes de sortie, l’opérande stdin `-`, le traitement de `--output`, la non-modification de l’entrée et la séparation entre la surface CLI et le cœur métier testable sans `argparse`.

## Bloqueurs à résoudre avant requirements, design, tasks et code

Le SpecBlock ne fournit pas les informations nécessaires pour produire des artefacts cohérents sans inventer de comportement :

1. `domain_contracts.command_contracts`, auquel la règle de JSONL invalide renvoie, est vide. La politique par commande (arrêt ou continuation, sortie partielle, diagnostics, code de sortie et plusieurs erreurs) est donc inconnue.
2. Le contrat canonique d’un événement est absent : champs requis, types, niveaux de sévérité, format et normalisation du timestamp, nullabilité et unicité ne sont pas définis. La sortie de `schema` ne peut donc pas être déterminée.
3. L’interface CLI par commande est incomplète : applicabilité des filtres, de `--output` et de `--redact`, valeurs et défaut de `--format`, sémantique des filtres et portée de la rédaction JSON ne sont pas précisées.
4. Les rendus et cas limites sont indéterminés : forme texte/JSON, encodage et nouvelle ligne, contexte local de `explain`, événement absent ou dupliqué, égalité de clés de tri et timestamps non normalisables.
5. La politique de fichier de sortie et les motifs/seuils de rédaction ne sont pas définis : écrasement, écriture atomique, répertoires absents, encodage, définition d’un token long et d’un identifiant hexadécimal long.
6. L’aide globale contient une règle permissive sur les fragments stables qui paraît moins stricte que l’objectif exigeant l’identification des quatre sous-commandes.

## Décision requise

Aucune exigence dérivée, aucun design, aucune tâche et aucun code ne sera généré tant que ces six points ne seront pas tranchés publiquement. Une décision peut soit compléter le SpecBlock, soit fournir un contrat explicite couvrant ces points.
