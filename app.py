"""
https://www.mongodb.com/developer/quickstart/python-quickstart-fastapi/
"""
import os
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from typing import Optional, List
import motor.motor_asyncio

app = FastAPI()

# We're using the async motor driver to create our MongoDB client.
# https://motor.readthedocs.io/en/stable/
client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])
# Then we specify our database name college.
db = client.college


class PyObjectId(ObjectId):
    """
    MongoDB stores data as BSON. https://www.mongodb.com/json-and-bson
    FastAPI encodes and decodes data as JSON strings.

    BSON has support for additional non-JSON-native data types, including
    ObjectId which can't be directly encoded as JSON. Because of this, we
    convert ObjectIds to strings before storing them as the _id.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class StudentModel(BaseModel):
    # MongoDB uses _id, but in Python, underscores at the start of attributes
    # have special meaning. If you have an attribute on your model that starts
    # with an underscore, pydantic (the data validation framework used by
    # FastAPI) will assume that it is a private variable, meaning you will not
    # be able to assign it a value! To get around this, we name the field id
    # but give it an alias of _id.
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

    name: str = Field(...)
    email: EmailStr = Field(...)
    course: str = Field(...)
    gpa: float = Field(..., le=4.0)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "Jane Doe",
                "email": "jdoe@example.com",
                "course": "Experiments, Science, and Fashion in Nanophotonics",
                "gpa": "3.0",
            }
        }


class UpdateStudentModel(BaseModel):
    """
    The UpdateStudentModel has two key differences from the StudentModel:

    It does not have an id attribute as this should never change.
    All fields are optional, so you only need to supply the fields you wish to
    update.
    """

    name: Optional[str]
    email: Optional[EmailStr]
    course: Optional[str]
    gpa: Optional[float]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "Jane Doe",
                "email": "jdoe@example.com",
                "course": "Experiments, Science, and Fashion in Nanophotonics",
                "gpa": "3.0",
            }
        }


@app.post("/", response_description="Add new student", response_model=StudentModel)
async def create_student(student: StudentModel = Body(...)):
    """
    The create_student route receives the new student data as a JSON string in
    a POST request.
    """
    # We have to decode this JSON request body into a Python dictionary before
    # passing it to our MongoDB client.
    student = jsonable_encoder(student)

    # The insert_one method response includes the _id of the newly created student.
    new_student = await db["students"].insert_one(student)

    # After we insert the student into our collection, we use the inserted_id to
    # find the correct document and return this in our JSONResponse.
    created_student = await db["students"].find_one({"_id": new_student.inserted_id})

    # FastAPI returns an HTTP 200 status code by default; but in this instance,
    # a 201 created is more appropriate.
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_student)


@app.get(
    "/", response_description="List all students", response_model=List[StudentModel]
)
async def list_students():
    # Motor's to_list method requires a max document count argument.
    # For this example, I have hardcoded it to 1000; but in a real application,
    # you would use the skip and limit parameters in find to paginate your results.
    # https://pymongo.readthedocs.io/en/3.11.0/api/pymongo/collection.html#pymongo.collection.Collection.find
    students = await db["students"].find().to_list(1000)
    return students


@app.get(
    "/{id}", response_description="Get a single student", response_model=StudentModel
)
async def show_student(id: str):
    """
    The student detail route has a path parameter of id, which FastAPI passes
    as an argument to the show_student function.
    """
    # We use the id to attempt to find the corresponding student in the database.
    # The conditional in this section is using an assignment expression, a
    # recent addition to Python (introduced in version 3.8) and often referred
    # to by the incredibly cute sobriquet "walrus operator."
    if (student := await db["students"].find_one({"_id": id})) is not None:
        return student

    # If a document with the specified id does not exist, we raise an
    # HTTPException with a status of 404.
    raise HTTPException(status_code=404, detail=f"Student {id} not found")


@app.put("/{id}", response_description="Update a student", response_model=StudentModel)
async def update_student(id: str, student: UpdateStudentModel = Body(...)):
    """
    The update_student route is like a combination of the create_student and
    the show_student routes. It receives the id of the document to update as
    well as the new data in the JSON body.
    """
    # We don't want to update any fields with empty values; so, first of all,
    # we iterate over all the items in the received dictionary and only add the
    # items that have a value to our new document.
    student = {k: v for k, v in student.dict().items() if v is not None}

    # If, after we remove the empty values, there are values to update, we use
    # update_one to $set the new values, and then return the updated document.
    # https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html#motor.motor_asyncio.AsyncIOMotorCollection.update_one
    # https://docs.mongodb.com/manual/reference/operator/update/set/
    if len(student) >= 1:
        update_result = await db["students"].update_one({"_id": id}, {"$set": student})

        if update_result.modified_count == 1:
            if (
                updated_student := await db["students"].find_one({"_id": id})
            ) is not None:
                return updated_student

    # However, if there are no fields left to update, we instead look for an
    # existing record that matches the id and return that unaltered.
    if (existing_student := await db["students"].find_one({"_id": id})) is not None:
        return existing_student

    # But if we get to the end of the function and we have not been able to
    # find a matching document to update or return, then we raise a 404 error
    # again.
    raise HTTPException(status_code=404, detail=f"Student {id} not found")


@app.delete("/{id}", response_description="Delete a student")
async def delete_student(id: str):
    """
    Again, because this is acting upon a single document, we have to supply an
    id in the URL.
    """
    delete_result = await db["students"].delete_one({"_id": id})

    # If we find a matching document and successfully delete it, then we return
    # an HTTP status of 204 or "No Content." In this case, we do not return a
    # document as we've already deleted it!
    if delete_result.deleted_count == 1:
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)

    # However, if we cannot find a student with the specified id, then instead
    # we return a 404.
    raise HTTPException(status_code=404, detail=f"Student {id} not found")
