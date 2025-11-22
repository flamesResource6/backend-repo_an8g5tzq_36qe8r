"""
Database Schemas for Car Rental Platform

Each Pydantic model corresponds to a MongoDB collection (lowercased class name).
Use these for validation when creating documents via helper functions.
"""
from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


class Car(BaseModel):
    brand: str = Field(..., description="Car brand, e.g., Tesla, Toyota")
    model: str = Field(..., description="Model name, e.g., Model 3, Corolla")
    type: Literal[
        "sedan", "suv", "coupe", "hatchback", "convertible", "truck", "van", "wagon", "sport"
    ] = Field(..., description="Body type")
    transmission: Literal["automatic", "manual"] = Field(...)
    fuel_type: Literal["petrol", "diesel", "hybrid", "electric"] = Field(...)
    seats: int = Field(..., ge=1, le=9)
    luggage: int = Field(2, ge=0, le=10)
    mileage: int = Field(0, ge=0, description="Mileage in km on odometer or avg range for EV")
    price_per_day: float = Field(..., ge=0)
    popularity: int = Field(0, ge=0)
    images: List[HttpUrl] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    available: bool = Field(True)
    description: Optional[str] = None


class User(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    license_no: Optional[str] = Field(None, description="Driver's license number")
    avatar_url: Optional[HttpUrl] = None


class Booking(BaseModel):
    user_id: str = Field(..., description="ID of the user")
    car_id: str = Field(..., description="ID of the car")
    pickup_location: str
    dropoff_location: str
    start_date: str = Field(..., description="ISO date string YYYY-MM-DD")
    end_date: str = Field(..., description="ISO date string YYYY-MM-DD")
    total_price: float = Field(..., ge=0)
    status: Literal["pending", "confirmed", "cancelled", "completed"] = "pending"
    payment_status: Literal["unpaid", "paid", "refunded"] = "unpaid"
    notes: Optional[str] = None


class Review(BaseModel):
    car_id: str
    user_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class Payment(BaseModel):
    booking_id: str
    amount: float = Field(..., ge=0)
    method: Literal["card", "paypal", "stripe", "cash"] = "card"
    status: Literal["initiated", "succeeded", "failed", "refunded"] = "initiated"
    transaction_id: Optional[str] = None
