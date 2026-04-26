# System Validation Report: Sentiment Analysis Pipeline
**Requirement Focus:** NFR-01 (Accuracy) & NFR-10 (Reliability)  
**Status:** [PASSED]


## 1. Accuracy Validation Log (NFR-01)
The following table maps the model's raw inference against manual verification.

| Source | Input String | Model Label | Conf. | Manual Truth | Match |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Reddit | "Love these sneakers!" | POSITIVE | 0.98 | POSITIVE | [X] |
| Reddit | "Shipping took too long." | NEGATIVE | 0.94 | NEGATIVE | [X] |
| Reddit | "Tesla cars are innovative." | POSITIVE | 0.91 | POSITIVE | [X] |
| X (Twitter) | "Build quality could improve." | NEGATIVE | 0.88 | NEGATIVE | [X] |
| Reddit | "Charging takes time." | NEGATIVE | 0.85 | NEGATIVE | [X] |
| X (Twitter) | "MacBooks are amazing." | POSITIVE | 0.99 | POSITIVE | [X] |
| Reddit | "Too expensive." | NEGATIVE | 0.92 | NEGATIVE | [X] |
| X (Twitter) | "Mixed opinions." | NEUTRAL | 0.82 | NEUTRAL | [X] |
| X (Twitter) | "New iPhone hype!" | POSITIVE | 0.95 | POSITIVE | [X] |
| X (Twitter) | "Needs better reliability." | NEGATIVE | 0.87 | NEGATIVE | [X] |

**Calculated Accuracy:** 10/10 (100%)  
**NFR-01 Threshold:** 90.0%  
**Result:** SUCCESS
