# apify-actor-assets

Image assets for our [Apify Store](https://apify.com/store) actor pages.

Apify has no screenshot gallery — every visual on an actor page is a markdown image inside that
actor's README, which Apify re-proxies through `images.apifyusercontent.com`. So each image needs
a publicly reachable source URL. This repository is that URL.

**It holds images and nothing else.** No source code, no credentials, no notes. The actors
themselves live in a private repository.

```
<actor-name>/<nn>-<slug>.png
```

Images are generated from HTML sources kept next to the actor, so any number on them can be
re-rendered when it changes. Consumed as:

```
https://raw.githubusercontent.com/dc83-lab/apify-actor-assets/main/<actor-name>/<file>.png
```

## Actors

| Directory | Actor |
|---|---|
| `clutch-b2b-intelligence/` | Clutch.co B2B agency directory scraper with an optional AI ICP-fit layer |
