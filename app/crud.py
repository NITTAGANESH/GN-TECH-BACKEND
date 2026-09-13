from sqlalchemy.orm import Session

from . import models


def get_or_create_customer(db: Session, phone: str, name: str | None = None) -> models.Customer:
    customer = db.query(models.Customer).filter(models.Customer.phone == phone).first()
    if customer:
        if name and not customer.name:
            customer.name = name
            db.commit()
            db.refresh(customer)
        return customer

    customer = models.Customer(phone=phone, name=name)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer
