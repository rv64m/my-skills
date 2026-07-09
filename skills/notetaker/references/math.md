# Mathematics Learning Notes

Use this reference when note synthesis is based on mathematics for algorithms,
machine learning, AI, data science, or quantitative technical work. Typical
signals include linear algebra, probability, statistics, calculus, optimization,
information theory, discrete math, graph theory, numerical methods, or
math-heavy ML papers and lectures.

The goal is durable mathematical understanding for algorithmic work, not a
rigid course-summary template. Do not force every note into the same section
layout. Instead, select the note blocks that fit the source and use computation
or visualization when they make the idea easier to verify or remember.

## Core Principles

- Adapt the note shape to the material. A theorem lecture, a worked example, a
  paper derivation, and a coding-oriented explanation need different notes.
- Separate **source definitions**, **source claims**, **proved results**,
  **assistant explanation**, **assistant inference**, and **numerical
  experiments**.
- Preserve assumptions, domains, dimensions, symbols, distributions, and
  boundary conditions. Most math mistakes in AI come from silently changing one
  of these.
- Prefer the smallest useful example. A 2D vector, a 2x2 matrix, a Bernoulli
  variable, or a one-parameter loss often teaches more than a large abstract
  case.
- Connect abstractions to operations: what can be computed, optimized,
  estimated, sampled, transformed, or compared?
- Use visuals when they clarify structure: geometry, distributions, loss
  landscapes, gradient paths, dependency graphs, or algorithm flow.
- Use Python for scientific computing when it verifies a claim, builds
  intuition, checks a derivation, or produces a teaching visualization.
- Do not create decorative figures. Every figure or computation should answer a
  specific learning question.
- Do not invent missing proof steps or stronger conclusions. If you fill gaps,
  label them as an inference or a standard result used for explanation.

## Classify the Source First

Before writing notes, classify the material. More than one class can apply.
Use this classification to decide which note blocks and visuals are worth
including.

| Class | Signals in source | Notes emphasis | Useful computation / visualization |
|---|---|---|---|
| Linear algebra | vectors, matrices, rank, basis, span, eigenvalues, SVD, projections, least squares | object shapes, transformations, geometry, decompositions, conditions for solvability | 2D transformations, projection diagrams, eigenvector plots, SVD/PCA examples |
| Probability | random variables, distributions, expectation, variance, conditional probability, Bayes, sampling | sample space, conditioning, independence, distributional assumptions, moments | PMF/PDF/CDF plots, Monte Carlo simulation, LLN/CLT demos, Bayesian update curves |
| Statistics / inference | estimators, likelihood, MLE/MAP, confidence intervals, hypothesis tests, regression | data-generating assumptions, estimator meaning, uncertainty, bias/variance | likelihood curves, sampling distributions, residual plots, bootstrap simulations |
| Calculus | derivative, integral, chain rule, Taylor expansion, Jacobian, Hessian | local approximation, sensitivity, multivariable shapes, change of variables | tangent plots, Taylor approximation error, vector fields, Jacobian action |
| Optimization | gradient descent, convexity, constraints, Lagrange multipliers, regularization, learning rate | objective, feasible set, update rule, convergence intuition, failure modes | contour plots, gradient paths, learning-rate comparison, convex/nonconvex examples |
| Information theory | entropy, cross entropy, KL divergence, mutual information, coding | uncertainty, surprise, distribution comparison, loss interpretation | entropy/KL curves, distribution comparison tables, cross-entropy examples |
| Discrete math / algorithms | graphs, trees, recurrence, DP, combinatorics, complexity, Markov chains | state, transition, invariant, recurrence, proof strategy, complexity | graph diagrams, state machines, DP tables, complexity growth plots |
| ML / AI math | loss functions, attention, embeddings, kernels, generative models, RL, diffusion, transformers | objective, tensor shapes, probabilistic interpretation, algorithmic role | tensor-shape flow, computation graph, toy model simulation, distribution evolution |

If classification is uncertain, say so briefly and write conservative learning
notes around definitions, assumptions, a minimal example, and open questions.

## Adaptive Note Blocks

Do not treat this as a required template. Choose blocks according to the source.
Omit blocks that would be filler.

### Learning target

Use when the material is part of a course, book chapter, or long lecture.
Capture what the learner should be able to do after studying it.

Good targets are operational:

- "Recognize when a matrix represents an orthogonal projection."
- "Derive the gradient of a least-squares objective."
- "Explain why cross entropy is a negative log-likelihood."
- "Simulate the central limit theorem and identify its assumptions."

### Prerequisites and dependency chain

Use when the source depends on earlier concepts. Keep it short and explicit:

- prerequisite concepts;
- concepts introduced here;
- concepts unlocked later.

This is especially useful for AI math, where a concept may first look abstract
but later becomes a building block for an algorithm.

### Symbols, shapes, and domains

Use when notation is dense or tensor/matrix dimensions matter. Record:

- symbol meaning;
- domain or type, such as scalar, vector, matrix, distribution, graph, function;
- shape, such as `x in R^d`, `W in R^{m x n}`, `P(Y | X)`;
- constraints, such as positive definite, orthonormal, independent, convex;
- whether a quantity is fixed, random, learned, estimated, or observed.

For ML and AI material, tensor shapes are often as important as formulas.

### Definitions and assumptions

Use for core concepts, theorems, algorithms, and probability/statistics claims.
State the assumption before the result. Examples:

- independence / identical distribution;
- differentiability / convexity / smoothness;
- full rank / invertibility / positive definiteness;
- finite expectation / variance;
- closed and bounded feasible set;
- train/test split or data-generation assumptions.

### Intuition

Use when the source is abstract or formula-heavy. Pick the view that fits:

- geometric intuition for linear algebra and optimization;
- sampling intuition for probability and statistics;
- local approximation for calculus;
- uncertainty / coding intuition for information theory;
- state-transition intuition for algorithms and Markov processes;
- tensor-flow intuition for neural networks.

Do not replace a definition with intuition. Put intuition next to the exact
statement so the learner can keep both.

### Derivation or proof map

Use when a derivation is central to the lesson. The note should explain the
path, not copy every algebraic line unless the skipped step is easy to get
wrong.

Good derivation notes include:

- goal: what is being solved or shown;
- starting assumptions;
- key transformation or identity;
- reason each major step is legal;
- final result;
- when the result stops applying.

For proofs, prefer a proof map:

- strategy;
- invariant or key lemma;
- contradiction / induction / construction / bound if used;
- critical step;
- counterexample if an assumption is removed.

### Minimal worked example

Use whenever an abstract concept can be made concrete. Good examples are small
enough to compute by hand:

- a 2x2 matrix for eigenvalues, inverse, determinant, rank, projection;
- a two-point or Bernoulli distribution for expectation and variance;
- a one-dimensional quadratic for gradient descent;
- a tiny graph for BFS, shortest path, Markov chain, or PageRank;
- a three-sample regression problem for least squares.

If the source includes a worked example, preserve it. If not, create a small
teaching example and label it as such.

### Python experiment

Use when numerical computation strengthens the note. Good uses include:

- verify a formula numerically;
- simulate a probability result;
- compare exact and approximate solutions;
- expose a failure case;
- show how an algorithm behaves as a parameter changes;
- generate a plot that makes the concept visible.

Keep experiments small, deterministic when possible, and tied to a question.
State parameters, sample size, random seed, and whether the data is source data
or synthetic.

### AI / algorithm connection

Use when the source is meant to support algorithms or AI. Connect the math to a
specific computational role:

- dot product -> similarity, attention scores, projections;
- matrix multiplication -> linear layers, feature transforms, batched compute;
- norm / distance -> regularization, nearest neighbors, loss functions;
- eigenvalues / SVD -> PCA, spectral methods, conditioning, stability;
- expectation -> risk, loss, policy value, Monte Carlo estimate;
- likelihood -> model fitting, MLE, cross entropy;
- gradient / chain rule -> backpropagation and optimization;
- Hessian / curvature -> Newton methods, conditioning, local loss shape;
- entropy / KL -> classification loss, variational inference, RL objectives;
- Markov chains -> MDPs, PageRank, sequence models, sampling.

Do not overclaim. If the source only gives the math concept, present AI
connections as learning context, not as claims made by the source.

### Common confusions

Use when concepts are easy to mix up. Examples:

- independence vs uncorrelated;
- conditional probability vs joint probability;
- variance vs standard deviation;
- PDF value vs probability mass;
- basis vs coordinates;
- eigenvectors vs singular vectors;
- rank vs dimension;
- gradient vs directional derivative;
- convex function vs convex optimization problem;
- cross entropy vs KL divergence;
- likelihood vs probability;
- estimator vs estimate;
- correlation vs causation.

### Review questions

Use a few questions to test understanding. Prefer questions that require
transfer, not recall:

- "What assumption breaks this theorem?"
- "Can you construct a 2D example?"
- "Which dimensions must match for this formula?"
- "How would this show up in a neural network?"
- "What would a numerical simulation look like?"
- "What changes if the variables are dependent?"

## Scientific Computing and Visualization Policy

Use `scripts/render_visual.py` for optional Stage 3 enrichment. Start with:

```bash
python3 scripts/render_visual.py check
```

For plots and numerical experiments, use the `mpl` subcommand. The snippet gets
`plt`, `np` / `numpy`, and `math` preloaded. If installed, it also gets
`scipy`, `stats`, `optimize`, `linalg`, `special`, `sympy` / `sy`, and
`pandas` / `pd`:

```bash
python3 scripts/render_visual.py mpl plot.py --name concept_demo --out ./viz_out
```

Use inline Markdown math for formulas by default:

```markdown
$$
\nabla_w \frac{1}{2}\lVert Xw - y\rVert_2^2 = X^\top(Xw - y)
$$
```

Only use the `formula` renderer when the note needs an actual formula image.

### Dependency boundaries

The default visualization dependency set is Matplotlib, NumPy, and Graphviz.
The script can detect and preload optional helpers: SciPy, SymPy, and pandas.
Do not assume seaborn, scikit-learn, statsmodels, or other scientific packages
are installed.

If a task truly benefits from an optional dependency:

1. check whether it is already available;
2. explain why the dependency is useful;
3. ask the user before installing it;
4. use `python3 scripts/render_visual.py install --optional <name>` or
   `--with-math` only after approval;
5. keep the note understandable even if the dependency is not used.

For most learning visuals, NumPy + Matplotlib is enough.

### When to compute

Use Python when one of these is true:

- the source gives a theorem that benefits from simulation;
- a formula has a shape or sign that can be checked numerically;
- a geometric concept is hard to see from notation alone;
- an optimization update is easier to understand as a path;
- a probability distribution or sampling result should be visualized;
- a small counterexample would prevent a common misunderstanding.

Avoid Python when it would only restate a formula or add noise. The note should
teach the math first; code supports the learning.

### Label computed artifacts

Every computed figure or table should say what it is:

- `source data` when based on data from the source;
- `reconstructed from source` when filling small missing details;
- `synthetic teaching example` when created to explain the concept;
- `numerical experiment` when it tests or illustrates a claim;
- `assistant inference` when the source did not make the connection directly.

For simulations, include random seed, sample size, and distribution parameters
when relevant.

## Visuals by Topic

### Linear algebra

Useful visuals and computations:

- draw vectors, spans, bases, projections, and orthogonal components;
- show how a 2x2 matrix transforms a grid or unit circle;
- plot eigenvectors before and after transformation;
- compare rank-deficient vs full-rank transformations;
- show least-squares projection geometry;
- demonstrate SVD/PCA with a small point cloud.

Always track dimensions. For matrix formulas, include shape checks when they
help prevent mistakes.

### Probability and statistics

Useful visuals and computations:

- PMF/PDF/CDF plots;
- histograms from Monte Carlo samples;
- law of large numbers and central limit theorem simulations;
- prior, likelihood, and posterior curves;
- likelihood surface or log-likelihood curve;
- confidence interval or bootstrap sampling visualization;
- bias/variance examples.

Always distinguish random variables, observed values, parameters, and
estimators. State independence and distributional assumptions explicitly.

### Calculus and optimization

Useful visuals and computations:

- function plus tangent line;
- Taylor approximation and approximation error;
- contour plot with gradient vectors;
- gradient descent path under different learning rates;
- convex vs nonconvex examples;
- constrained optimization geometry;
- regularization effect on fitted parameters.

Always identify the objective, variables, constraints, and update rule. For
optimization algorithms, include failure modes such as bad scaling, poor
learning rate, saddle points, local minima, or nonconvexity when relevant.

### Information theory

Useful visuals and computations:

- entropy of Bernoulli distribution as `p` changes;
- cross entropy under wrong predicted probability;
- KL divergence between simple distributions;
- mutual information as dependence changes.

Always clarify which distribution is the data/source distribution and which is
the model/approximation distribution. Order matters for KL divergence.

### Discrete math and algorithms

Useful visuals and computations:

- graph, tree, or state-machine diagrams with Graphviz or Mermaid;
- dynamic-programming table;
- recurrence expansion tree;
- complexity growth comparison;
- Markov transition matrix and stationary distribution examples.

Keep algorithm notes tied to invariants, state transitions, recurrence
relations, or complexity arguments. Do not reduce them to code summaries.

### ML and AI math

Useful visuals and computations:

- tensor-shape flow through a model block;
- computation graph for forward and backward passes;
- toy loss and gradient path;
- attention score and softmax example;
- embedding similarity example;
- probabilistic graphical model or dependency diagram;
- diffusion or sampling process schematic when source supports it.

Connect the concept to the algorithmic role, but keep source claims separate
from broader assistant-provided context.

## Formula and Notation Rules

- Use LaTeX for important formulas.
- Define every symbol that is not obvious from the surrounding text.
- Preserve vector/matrix orientation when it matters.
- Include domains and dimensions for linear algebra and ML formulas.
- Include assumptions next to the theorem or result, not buried later.
- For probability, distinguish `P(A | B)` from `P(A, B)` and state the sample
  space when ambiguity matters.
- For calculus and optimization, identify which variable the derivative is
  taken with respect to.
- For statistics, distinguish population quantity, sample statistic,
  parameter, estimator, and estimate.

## Wording Guidelines

Use learning-oriented language:

- Good: "The source defines this under the assumption that..."
- Good: "A useful way to see the result is..."
- Good: "This numerical experiment uses synthetic data to illustrate..."
- Good: "This AI connection is not stated by the source, but it is a standard
  place where the concept appears."
- Bad: "This formula always works."
- Bad: "The simulation proves the theorem."
- Bad: "The source shows this applies to all neural networks."

Numerical experiments illustrate or sanity-check; they do not replace proof.

## Final Output Checklist

Before finishing math notes, verify:

- The notes are not forced into a rigid template.
- Important assumptions, domains, and dimensions are preserved.
- Definitions, intuition, derivations, examples, and AI connections are clearly
  separated when they appear.
- Any assistant-created example is labeled as a teaching example.
- Any Python result is labeled as a numerical experiment or synthetic example.
- Figures teach a specific concept and are not decorative.
- Optional dependencies were not assumed without checking or user approval.
- Formula notation is consistent and symbols are defined.
- At least one minimal example, visual, or review question is included when the
  material is abstract enough to need it.
