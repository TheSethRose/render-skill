---
title: Quarterly Platform Review
subtitle: What changed, what broke, and what we're doing next
author: Platform Team
date: October 2026
---

The platform team shipped four major changes this quarter. Most went smoothly; one didn't. This review covers the results, the incident on September 3rd, and the plan for Q4.[^scope]

## Summary

Latency dropped by **38%** after the cache rewrite, and the queue migration finished two weeks early. The one serious problem — a 47-minute outage during the auth rollout — came from a config value that differed between staging and production.

> The best outcome of this quarter wasn't the speed-up. It was learning that staging had quietly stopped matching production, and fixing that before it cost us more.

### Key numbers

| Metric           | Q2     | Q3     | Change  |
|------------------|-------:|-------:|--------:|
| p50 latency (ms) | 142    | 88     | −38%    |
| p99 latency (ms) | 1,210  | 640    | −47%    |
| Uptime           | 99.94% | 99.89% | −0.05pt |
| Deploys per week | 11     | 19     | +73%    |

## What we shipped

1. **Cache rewrite.** Replaced the read-through cache with a write-behind design.
2. **Queue migration.** Moved all background jobs to the new queue.
3. **Config drift check.** Blocks deploys when staging and production differ.

```python
def check_drift(staging: dict, prod: dict, allowed: set[str]) -> list[str]:
    """Return keys whose values differ, except those we expect to differ."""
    return sorted(k for k in staging.keys() | prod.keys()
                  if k not in allowed and staging.get(k) != prod.get(k))
```

## Next quarter

- [x] Finish the queue migration
- [ ] Retire the old queue
- [ ] Bring p99 under 500 ms

[^scope]: Core platform only. The data pipeline has its own review.
