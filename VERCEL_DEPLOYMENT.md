# Vercel deployment notes

This is a reduced deployment copy of the Flask application. Runtime code, templates, static assets, the trained model, scaler, CSV dataset, and AgriShield JSON records are retained. Git metadata, the local `.env`, scratch extraction code, Python bytecode caches, and the offline model-training script are excluded from deployment packaging.

## Deploy

1. Import this folder as the project root in Vercel, or deploy this folder with the Vercel CLI.
2. Keep the Python runtime at 3.12 (`.python-version`).
3. If the build reports an oversized function, enable Vercel Large Functions for the project. For an existing project, add `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` in Project Settings → Environment Variables, then redeploy. Large Functions are a Vercel beta and require Fluid Compute.
4. The local `.env` contained only Flask development settings; it is intentionally omitted. Configure no `.env` file in production. Keep Flask debug mode disabled in production.

`vercel.json` is the exact project configuration. `requirements.txt` retains the project's runtime dependencies, including TensorFlow for the LSTM forecast. TensorFlow and its compiled numerical dependencies are the likely source of the reported ~2.15 GB installed/deployment footprint; the uploaded ZIP itself expands to only about 9.4 MB. The source archive alone cannot establish the exact size of Vercel's built function, which depends on its resolved Linux wheels and runtime layers.
