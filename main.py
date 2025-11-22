import os
from typing import List, Optional, Any, Dict
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Car Rental API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utilities
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    for k, v in list(doc.items()):
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc


# Schemas for requests
class CarFilters(BaseModel):
    type: Optional[str] = None
    brand: Optional[str] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    seats_gte: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sort: Optional[str] = Field(None, description="price_asc|price_desc|popularity|newest")


class BookingRequest(BaseModel):
    user_id: str
    car_id: str
    pickup_location: str
    dropoff_location: str
    start_date: str
    end_date: str
    total_price: float
    notes: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Car Rental Backend Running"}


@app.get("/api/cars")
def list_cars(
    type: Optional[str] = None,
    brand: Optional[str] = None,
    transmission: Optional[str] = None,
    fuel_type: Optional[str] = None,
    seats_gte: Optional[int] = Query(None, ge=1, le=9),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    sort: Optional[str] = Query(None, description="price_asc|price_desc|popularity|newest"),
    limit: int = Query(50, ge=1, le=200),
):
    if db is None:
        # Return mocked data so frontend still previews nicely
        demo = [
            {
                "id": "demo-1",
                "brand": "Tesla",
                "model": "Model 3",
                "type": "sedan",
                "transmission": "automatic",
                "fuel_type": "electric",
                "seats": 5,
                "luggage": 3,
                "mileage": 12000,
                "price_per_day": 89,
                "popularity": 98,
                "images": [
                    "https://images.unsplash.com/photo-1511390420183-3a2c5a36f3f1?q=80&w=1200&auto=format&fit=crop"
                ],
                "features": ["Autopilot", "Bluetooth", "A/C"],
                "available": True,
                "description": "Sleek EV with long range and premium comfort.",
            },
            {
                "id": "demo-2",
                "brand": "BMW",
                "model": "X5",
                "type": "suv",
                "transmission": "automatic",
                "fuel_type": "hybrid",
                "seats": 5,
                "luggage": 4,
                "mileage": 24000,
                "price_per_day": 129,
                "popularity": 92,
                "images": [
                    "https://images.unsplash.com/photo-1619767886558-efdc259cde1c?q=80&w=1200&auto=format&fit=crop"
                ],
                "features": ["Panoramic Roof", "Leather", "GPS"],
                "available": True,
                "description": "Luxury SUV perfect for family trips.",
            },
        ]
        return {"items": demo[:limit], "count": len(demo[:limit])}

    query: Dict[str, Any] = {}
    if type:
        query["type"] = type
    if brand:
        query["brand"] = brand
    if transmission:
        query["transmission"] = transmission
    if fuel_type:
        query["fuel_type"] = fuel_type
    if seats_gte is not None:
        query["seats"] = {"$gte": seats_gte}
    if min_price is not None or max_price is not None:
        price_q: Dict[str, Any] = {}
        if min_price is not None:
            price_q["$gte"] = min_price
        if max_price is not None:
            price_q["$lte"] = max_price
        query["price_per_day"] = price_q

    sort_map = {
        "price_asc": ("price_per_day", 1),
        "price_desc": ("price_per_day", -1),
        "popularity": ("popularity", -1),
        "newest": ("created_at", -1),
    }

    cursor = db["car"].find(query)
    if sort and sort in sort_map:
        field, direction = sort_map[sort]
        cursor = cursor.sort(field, direction)
    cursor = cursor.limit(limit)

    items = [serialize_doc(doc) for doc in cursor]
    return {"items": items, "count": len(items)}


@app.get("/api/cars/{car_id}")
def get_car(car_id: str):
    if db is None:
        # return a demo car
        return {
            "id": car_id,
            "brand": "Tesla",
            "model": "Model 3 Performance",
            "type": "sedan",
            "transmission": "automatic",
            "fuel_type": "electric",
            "seats": 5,
            "luggage": 3,
            "mileage": 12000,
            "price_per_day": 99,
            "popularity": 99,
            "images": [
                "https://images.unsplash.com/photo-1511390420183-3a2c5a36f3f1?q=80&w=1200&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1549921296-3c2b3f6b33b5?q=80&w=1200&auto=format&fit=crop",
            ],
            "features": ["Autopilot", "Heated Seats", "Premium Audio"],
            "available": True,
            "description": "Performance EV with thrilling acceleration.",
            "reviews": [
                {"user": "Alex", "rating": 5, "comment": "Amazing ride!"},
                {"user": "Sam", "rating": 4, "comment": "Very comfortable."},
            ],
        }

    try:
        oid = ObjectId(car_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid car id")

    doc = db["car"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Car not found")
    return serialize_doc(doc)


@app.post("/api/bookings")
def create_booking(payload: BookingRequest):
    if db is None:
        # Mock booking id
        return {"id": "demo-booking-123", "status": "pending", **payload.model_dump()}

    # Validate car exists
    try:
        car_oid = ObjectId(payload.car_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid car id")

    car = db["car"].find_one({"_id": car_oid})
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    data = payload.model_dump()
    inserted_id = create_document("booking", data)
    doc = db["booking"].find_one({"_id": ObjectId(inserted_id)})
    return serialize_doc(doc)


@app.get("/api/bookings")
def list_bookings(user_id: Optional[str] = None, limit: int = Query(50, ge=1, le=200)):
    if db is None:
        demo = [
            {
                "id": "demo-book-1",
                "user_id": "u1",
                "car_id": "demo-1",
                "pickup_location": "Downtown",
                "dropoff_location": "Airport",
                "start_date": "2025-12-01",
                "end_date": "2025-12-05",
                "total_price": 356,
                "status": "confirmed",
                "payment_status": "paid",
            }
        ]
        return {"items": demo[:limit], "count": len(demo[:limit])}

    query: Dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id
    cursor = db["booking"].find(query).sort("created_at", -1).limit(limit)
    items = [serialize_doc(doc) for doc in cursor]
    return {"items": items, "count": len(items)}


@app.post("/api/seed")
def seed_demo_cars():
    if db is None:
        return {"status": "no-db", "message": "Database not configured in this environment"}
    if db["car"].count_documents({}) > 0:
        return {"status": "ok", "message": "Cars already exist"}

    cars = [
        {
            "brand": "Tesla",
            "model": "Model 3",
            "type": "sedan",
            "transmission": "automatic",
            "fuel_type": "electric",
            "seats": 5,
            "luggage": 3,
            "mileage": 12000,
            "price_per_day": 89,
            "popularity": 98,
            "images": [
                "https://images.unsplash.com/photo-1511390420183-3a2c5a36f3f1?q=80&w=1200&auto=format&fit=crop"
            ],
            "features": ["Autopilot", "Bluetooth", "A/C"],
            "available": True,
            "description": "Sleek EV with long range and premium comfort.",
        },
        {
            "brand": "BMW",
            "model": "X5",
            "type": "suv",
            "transmission": "automatic",
            "fuel_type": "hybrid",
            "seats": 5,
            "luggage": 4,
            "mileage": 24000,
            "price_per_day": 129,
            "popularity": 92,
            "images": [
                "https://images.unsplash.com/photo-1619767886558-efdc259cde1c?q=80&w=1200&auto=format&fit=crop"
            ],
            "features": ["Panoramic Roof", "Leather", "GPS"],
            "available": True,
            "description": "Luxury SUV perfect for family trips.",
        },
        {
            "brand": "Toyota",
            "model": "Corolla",
            "type": "sedan",
            "transmission": "automatic",
            "fuel_type": "petrol",
            "seats": 5,
            "luggage": 3,
            "mileage": 40000,
            "price_per_day": 49,
            "popularity": 85,
            "images": [
                "https://images.unsplash.com/photo-1549921296-3c2b3f6b33b5?q=80&w=1200&auto=format&fit=crop"
            ],
            "features": ["Great MPG", "A/C", "USB"],
            "available": True,
            "description": "Reliable and efficient daily driver.",
        },
    ]
    db["car"].insert_many(cars)
    return {"status": "ok", "inserted": len(cars)}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "❌ Not Configured"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Env flags
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
