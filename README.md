MongoDB with FastAPI
===

This is a small sample project demonstrating how to build an API with [MongoDB](https://developer.mongodb.com/) and [FastAPI](https://fastapi.tiangolo.com/).
It was written to accompany a [blog post](https://developer.mongodb.com/quickstart/python-quickstart-fastapi/) - you should go read it!

Usage
---

```bash
# Install the requirements:
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure the location of your MongoDB database:
export MONGODB_URL="mongodb+srv://<username>:<password>@<url>/<db>?retryWrites=true&w=majority"

# Start the service:
python -m uvicorn app:app --reload  # without `python -m` the multiprocessing library tries to use system python instead of venv
```

(Check out [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) if you need a MongoDB database.)

Now you can load <http://localhost:8000> in your browser ... but there won't be much to see until you've inserted some data. (OpenAPI documentation is at <http://localhost:8000/docs>.)

If you have any questions or suggestions, check out the [MongoDB Community Forums](https://developer.mongodb.com/community/forums/)!
