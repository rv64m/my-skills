# Trading Learning Notes

Use this reference when note synthesis is based on trading, investing, market
structure, technical analysis, quantitative trading, backtesting, risk
management, or trading psychology material.

## Core Principles

- Separate **source facts**, **author claims**, **assistant inference**, and
  **open questions**.
- Preserve the source's market, timeframe, instrument, session, and data
  assumptions when available.
- Explain the condition under which an idea is supposed to work, and the
  condition under which it fails.
- Prefer visual notes whenever a chart, table, payoff diagram, flowchart, or
  formula would make the idea easier to learn.
- Label every chart as one of: `source data`, `reconstructed from source`,
  `synthetic teaching example`, or `conceptual diagram`.

## Adapt Notes to the Source

Before writing, identify the source's main concepts, evidence, assumptions,
and learning needs. Use the relevant guidance below without requiring the
material to fit a predefined category. Topics may overlap, and the examples
in this reference are not exhaustive.

Choose note emphasis and visuals from the source itself—for example, explain
rule mechanics for a strategy, execution tradeoffs for order-flow material,
or behavioral interventions for trading-process material. When the appropriate
emphasis is uncertain, use the general principles and only add visuals that
clarify a specific concept.

## Visual Enrichment Rules

Use as many useful visuals as the source supports. Prefer a compact chart over
paragraphs when it reduces ambiguity.

Good visuals include:

- Candlestick patterns and annotated OHLC sequences.
- Support/resistance, trendline, breakout, pullback, and range diagrams.
- Entry / stop / target / invalidation overlays.
- Risk/reward diagrams and R-multiple examples.
- Position sizing tables by account size, stop distance, and risk percent.
- Equity curve, drawdown curve, rolling returns, and return distribution.
- Signal-generation flowcharts and trade-management decision trees.
- Timeline charts for case studies and trade reviews.
- Tables contrasting valid setup, weak setup, false breakout, and failed setup.

## Candlestick Chart Rules

### Data priority

1. **Real OHLCV data from source**: plot the actual data. Preserve dates,
   instrument, timeframe, and source attribution.
2. **Partial source data**: reconstruct only the missing values needed for a
   teaching diagram. Label as `reconstructed from source`.
3. **No OHLC data, only a named pattern**: generate a small synthetic teaching
   example. Label as `synthetic teaching example; not market data`.
4. **Pure concept without price sequence**: use a flowchart or table instead of
   fake candles.

### Candlestick style

- Use green/red or hollow/filled candles consistently.
- Show wick, body, open, high, low, close clearly.
- Annotate the key candle(s), level(s), volume clue, entry trigger, stop, target,
  and invalidation when they are part of the source.
- Include the timeframe and whether the picture is source data or synthetic in
  the caption.
- For synthetic patterns, keep the data minimal: usually 5-12 candles are enough.

### Common synthetic patterns to draw

Draw a teaching example when the source mentions:

- Hammer / inverted hammer / shooting star / hanging man.
- Bullish or bearish engulfing.
- Morning star / evening star.
- Doji, long-legged doji, spinning top.
- Pin bar, inside bar, outside bar.
- Breakout, failed breakout, pullback, retest.
- Double top / double bottom.
- Head and shoulders / inverse head and shoulders.
- Cup and handle, wedge, flag, pennant, triangle, range.

Always add the pattern's required context. Example: a hammer after a decline is
not the same lesson as a hammer inside a range.

## Chart Generation With `render_visual.py`

Use `scripts/render_visual.py mpl` for Matplotlib charts. Avoid new dependencies
unless the user approves. A candlestick chart can be drawn with plain
Matplotlib patches.

Example synthetic candlestick snippet:

```bash
python3 scripts/render_visual.py mpl candle_hammer.py --name hammer_example --out ./viz_out
```

```python
from matplotlib.patches import Rectangle

ohlc = [
    (10.0, 10.3, 9.7, 9.8),
    (9.8, 10.0, 9.2, 9.4),
    (9.4, 9.6, 8.7, 8.9),
    (8.9, 9.2, 8.2, 8.5),
    (8.55, 8.8, 7.4, 8.75),  # hammer
    (8.75, 9.4, 8.7, 9.3),
]

fig, ax = plt.subplots(figsize=(7, 3.8))
width = 0.55
for i, (open_, high, low, close) in enumerate(ohlc):
    up = close >= open_
    color = "#218c5a" if up else "#c44536"
    ax.vlines(i, low, high, color=color, linewidth=1.5)
    body_low = min(open_, close)
    body_height = max(abs(close - open_), 0.03)
    ax.add_patch(Rectangle((i - width / 2, body_low), width, body_height,
                           facecolor=color, edgecolor=color, alpha=0.85))

ax.annotate("Hammer: long lower shadow after decline",
            xy=(4, 8.75), xytext=(2.2, 9.9),
            arrowprops={"arrowstyle": "->", "color": "#333333"},
            fontsize=9)
ax.axhline(8.2, color="#555555", linestyle="--", linewidth=1)
ax.text(0, 8.25, "prior swing low / invalidation area", fontsize=8)
ax.set_title("Synthetic hammer example - not market data")
ax.set_xticks(range(len(ohlc)))
ax.set_xticklabels([f"C{i+1}" for i in range(len(ohlc))])
ax.set_ylabel("Price")
ax.grid(True, axis="y", alpha=0.25)
fig.tight_layout()
```

Then embed the returned Markdown image link in the notes. The caption must say
whether it is synthetic or source data.

## Chart Types by Topic

### Technical analysis / price action

- Candlestick pattern diagram.
- Annotated support/resistance chart.
- Trendline, channel, range, breakout, pullback, and retest diagram.
- Volume confirmation or divergence chart when volume is discussed.
- Pattern comparison table: valid setup vs false signal.

Include:

- Prior trend or market regime.
- Trigger candle or confirmation condition.
- Invalidation level.
- Common false positives.

### Systematic / quantitative trading

- Rule flowchart: data -> filter -> signal -> sizing -> exit -> review.
- Equity curve and drawdown curve if backtest results are provided.
- Return distribution, win/loss distribution, holding-period distribution.
- Parameter sensitivity heatmap if the source discusses optimization.
- Train/test or in-sample/out-of-sample split diagram.

Include:

- Exact rule definitions.
- Transaction cost, slippage, liquidity, survivorship, and lookahead caveats.
- Metrics: CAGR, max drawdown, Sharpe/Sortino, win rate, payoff ratio,
  profit factor, exposure, turnover, sample size.

### Risk management / position sizing

- Risk/reward diagram marking entry, stop, target, and R multiple.
- Position-size table:
  `position size = account equity * risk percent / stop distance`.
- Drawdown path showing how consecutive losses affect equity.
- Scenario table for best/base/worst outcomes.

Include:

- Risk per trade and portfolio-level exposure.
- Correlation and concentration risk.
- Gap, liquidity, leverage, and margin risk.

### Trading psychology / process

- Behavior loop diagram: trigger -> impulse -> action -> result -> review.
- Decision checklist before entry and after exit.
- Table mapping bias to symptom and countermeasure.
- Journal template for repeatable review.

Include:

- Observable behaviors, not vague personality judgments.
- Concrete intervention: wait rule, checklist, sizing cap, cooldown, review tag.

### Market microstructure / execution

- Order-book or spread diagram.
- Slippage chart by order size or volatility when data exists.
- Flowchart of market order, limit order, stop order, stop-limit order.
- Auction/session timeline when the source discusses opening/closing auctions.

Include:

- Who provides liquidity and who takes it.
- Spread, depth, queue priority, impact, and execution risk.

### Trade review / case study

- Annotated trade chart with entry, stop, target, exit, and invalidation.
- Timeline: plan -> trigger -> execution -> management -> exit -> review.
- Table: planned action, actual action, difference, lesson.

Include:

- Whether the trade followed the plan.
- Whether outcome quality and decision quality differed.
- What should be monitored next time.

## Formulas and Tables

Use formulas when they clarify the mechanics:

```markdown
$$
R = \frac{\text{exit price} - \text{entry price}}{\text{entry price} - \text{stop price}}
$$

$$
\text{position size} =
\frac{\text{account equity} \times \text{risk percent}}{\text{entry price} - \text{stop price}}
$$
```

Use tables for comparisons:

| Item | What to capture |
|---|---|
| Setup | Pattern, context, required confirmation |
| Invalidation | The condition that proves the idea wrong |
| Risk | Stop, position size, loss scenario |
| Evidence | Source data, backtest metric, example count |
| Caveat | Regime, sample size, cost, execution issue |

## Safety and Wording

Use learning-oriented language:

- Good: "The source argues that this pattern may indicate..."
- Good: "A learner should verify this with data before using it."
- Good: "This is a synthetic diagram for recognizing the structure."
- Bad: "Buy when this pattern appears."
- Bad: "This setup is profitable."
- Bad: "This chart proves the strategy works."

When the material contains strong claims, add a verification note:

- What data would be needed?
- What sample size is available?
- What market regime was covered?
- Were costs, slippage, liquidity, and survivorship considered?
- Could the rule be overfit?
