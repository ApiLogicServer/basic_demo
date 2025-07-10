"""
PROCEDURAL BUSINESS LOGIC IMPLEMENTATION
=======================================

This file shows how to implement business logic using traditional
procedural code instead of LogicBank declarative rules.

Business Requirements:
1. Copy unit_price from Product to Item
2. Calculate Item amount = quantity * unit_price  
3. Calculate Order total = sum of Item amounts
4. Update Customer balance = sum of unshipped Order totals
5. Ensure Customer balance ≤ credit_limit

"""

from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import event
from database import models
import logging

app_logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for business rule violations"""
    pass

class ProceduralBusinessLogic:
    """
    Procedural implementation of business logic.
    
    This requires manually handling all the complexity that LogicBank
    handles automatically:
    - Event handling
    - Multi-table calculations
    - Constraint checking
    - Cascade updates
    - Transaction management
    """
    
    @staticmethod
    def copy_unit_price_from_product(item: models.Item, session: Session):
        """
        Rule 1: Copy unit_price from Product to Item
        """
        if item.product_id:
            product = session.query(models.Product).get(item.product_id)
            if product:
                old_price = item.unit_price
                item.unit_price = product.unit_price
                if old_price != item.unit_price:
                    app_logger.info(f"Updated unit_price from {old_price} to {product.unit_price} for item {item.id} from product {product.id}")
    
    @staticmethod
    def calculate_item_amount(item: models.Item):
        """
        Rule 2: Calculate Item amount = quantity * unit_price
        """
        if item.quantity is not None and item.unit_price is not None:
            old_amount = item.amount
            item.amount = Decimal(item.quantity) * Decimal(item.unit_price)
            if old_amount != item.amount:
                app_logger.info(f"Item {item.id} amount changed from {old_amount} to {item.amount}")
    
    @staticmethod
    def calculate_order_total(order: models.Order, session: Session):
        """
        Rule 3: Calculate Order total = sum of Item amounts
        """
        # Must reload items to get current amounts
        items = session.query(models.Item).filter_by(order_id=order.id).all()
        old_total = order.amount_total
        order.amount_total = sum(Decimal(item.amount or 0) for item in items)
        if old_total != order.amount_total:
            app_logger.info(f"Order {order.id} total changed from {old_total} to {order.amount_total}")
    
    @staticmethod
    def update_customer_balance(customer: models.Customer, session: Session):
        """
        Rule 4: Update Customer balance = sum of unshipped Order totals
        """
        # Must reload orders to get current totals
        orders = session.query(models.Order).filter_by(
            customer_id=customer.id,
            date_shipped=None
        ).all()
        old_balance = customer.balance
        customer.balance = sum(Decimal(order.amount_total or 0) for order in orders)
        if old_balance != customer.balance:
            app_logger.info(f"Customer {customer.id} balance changed from {old_balance} to {customer.balance}")
    
    @staticmethod
    def validate_credit_limit(customer: models.Customer):
        """
        Rule 5: Ensure Customer balance ≤ credit_limit
        """
        if customer.balance and customer.credit_limit:
            if customer.balance > customer.credit_limit:
                raise ValidationError(
                    f"Customer balance ({customer.balance}) exceeds credit limit ({customer.credit_limit})"
                )

# =============================================================================
# PROCEDURAL EVENT HANDLERS
# =============================================================================
# These must be manually registered and handle all the cascading logic

def handle_item_insert(mapper, connection, target: models.Item):
    """Handle Item insertion - must manually cascade all effects"""
    session = Session.object_session(target)
    if not session:
        return
    
    try:
        # Rule 1: Copy unit price from product
        ProceduralBusinessLogic.copy_unit_price_from_product(target, session)
        
        # Rule 2: Calculate item amount
        ProceduralBusinessLogic.calculate_item_amount(target)
        
        # Rule 3: Update order total (if order exists)
        if target.order_id:
            order = session.query(models.Order).get(target.order_id)
            if order:
                ProceduralBusinessLogic.calculate_order_total(order, session)
                
                # Rule 4: Update customer balance
                customer = session.query(models.Customer).get(order.customer_id)
                if customer:
                    ProceduralBusinessLogic.update_customer_balance(customer, session)
                    
                    # Rule 5: Validate credit limit
                    ProceduralBusinessLogic.validate_credit_limit(customer)
        
    except Exception as e:
        app_logger.error(f"Error in item insert handler: {e}")
        raise

def handle_item_update(mapper, connection, target: models.Item):
    """Handle Item updates - must manually cascade all effects AND handle product changes"""
    session = Session.object_session(target)
    if not session:
        return
    
    try:
        # Get the OLD version of the item to detect changes
        old_item = session.query(models.Item).get(target.id)
        
        # Check if product_id changed (CRITICAL BUG FIX)
        product_changed = old_item and old_item.product_id != target.product_id
        
        if product_changed:
            # Copy NEW unit_price from NEW product
            ProceduralBusinessLogic.copy_unit_price_from_product(target, session)
            app_logger.info(f"Item {target.id} product changed from {old_item.product_id} to {target.product_id}")
        
        # Rule 2: Recalculate item amount (with potentially new unit_price)
        ProceduralBusinessLogic.calculate_item_amount(target)
        
        # Handle order_id changes too (another potential bug!)
        order_changed = old_item and old_item.order_id != target.order_id
        
        if order_changed and old_item.order_id:
            # Update OLD order total (remove this item)
            old_order = session.query(models.Order).get(old_item.order_id)
            if old_order:
                ProceduralBusinessLogic.calculate_order_total(old_order, session)
                # Update old customer balance
                old_customer = session.query(models.Customer).get(old_order.customer_id)
                if old_customer:
                    ProceduralBusinessLogic.update_customer_balance(old_customer, session)
                    ProceduralBusinessLogic.validate_credit_limit(old_customer)
        
        # Rule 3: Update NEW order total
        if target.order_id:
            order = session.query(models.Order).get(target.order_id)
            if order:
                ProceduralBusinessLogic.calculate_order_total(order, session)
                
                # Rule 4: Update customer balance
                customer = session.query(models.Customer).get(order.customer_id)
                if customer:
                    ProceduralBusinessLogic.update_customer_balance(customer, session)
                    
                    # Rule 5: Validate credit limit
                    ProceduralBusinessLogic.validate_credit_limit(customer)
        
    except Exception as e:
        app_logger.error(f"Error in item update handler: {e}")
        raise

def handle_item_delete(mapper, connection, target: models.Item):
    """Handle Item deletion - must manually cascade all effects"""
    session = Session.object_session(target)
    if not session:
        return
    
    try:
        # Rule 3: Update order total
        if target.order_id:
            order = session.query(models.Order).get(target.order_id)
            if order:
                ProceduralBusinessLogic.calculate_order_total(order, session)
                
                # Rule 4: Update customer balance
                customer = session.query(models.Customer).get(order.customer_id)
                if customer:
                    ProceduralBusinessLogic.update_customer_balance(customer, session)
                    
                    # Rule 5: Validate credit limit
                    ProceduralBusinessLogic.validate_credit_limit(customer)
        
    except Exception as e:
        app_logger.error(f"Error in item delete handler: {e}")
        raise

def handle_order_update(mapper, connection, target: models.Order):
    """Handle Order updates - check for shipping changes AND customer changes"""
    session = Session.object_session(target)
    if not session:
        return
    
    try:
        # Get the OLD version of the order to detect changes
        old_order = session.query(models.Order).get(target.id)
        
        # Check if customer_id changed (CRITICAL BUG FIX)
        customer_changed = old_order and old_order.customer_id != target.customer_id
        
        if customer_changed:
            # Update OLD customer balance (remove this order)
            old_customer = session.query(models.Customer).get(old_order.customer_id)
            if old_customer:
                ProceduralBusinessLogic.update_customer_balance(old_customer, session)
                ProceduralBusinessLogic.validate_credit_limit(old_customer)
                app_logger.info(f"Order {target.id} moved from customer {old_customer.id} to {target.customer_id}")
        
        # Update NEW customer balance (always needed for shipping status or customer changes)
        new_customer = session.query(models.Customer).get(target.customer_id)
        if new_customer:
            ProceduralBusinessLogic.update_customer_balance(new_customer, session)
            ProceduralBusinessLogic.validate_credit_limit(new_customer)
        
    except Exception as e:
        app_logger.error(f"Error in order update handler: {e}")
        raise

# =============================================================================
# REGISTER EVENT HANDLERS
# =============================================================================
# Must manually register all these handlers

def register_procedural_logic():
    """
    Register all procedural event handlers.
    
    This replaces the declarative rules with procedural code.
    Note: This is much more complex and error-prone than LogicBank rules.
    """
    
    # Item events
    event.listen(models.Item, 'before_insert', handle_item_insert)
    event.listen(models.Item, 'before_update', handle_item_update)
    event.listen(models.Item, 'before_delete', handle_item_delete)
    
    # Order events  
    event.listen(models.Order, 'before_update', handle_order_update)
    
    app_logger.info("Procedural business logic handlers registered")

# =============================================================================
# COMPARISON SUMMARY
# =============================================================================
"""
LINES OF CODE COMPARISON:

LogicBank Declarative Rules:
    ~15 lines of clean, readable rules

Procedural Implementation (this file):
    ~220+ lines of complex event handling code

KEY DIFFERENCES:

1. COMPLEXITY:
   - LogicBank: Simple rule declarations
   - Procedural: Complex event handling with manual cascading

2. MAINTAINABILITY:
   - LogicBank: Rules are self-documenting
   - Procedural: Hard to understand the business logic flow

3. ERROR HANDLING:
   - LogicBank: Automatic transaction rollback
   - Procedural: Manual error handling and rollback

4. PERFORMANCE:
   - LogicBank: Optimized SQL with pruning/optimization
   - Procedural: Multiple queries, potential N+1 problems

5. DEBUGGING:
   - LogicBank: Clear rule execution logs
   - Procedural: Hard to trace through event handlers

6. TESTING:
   - LogicBank: Test rules independently
   - Procedural: Must test entire event chain

7. BUSINESS ALIGNMENT:
   - LogicBank: Rules match business requirements
   - Procedural: Implementation details obscure business logic

CONCLUSION:
LogicBank provides 15x+ reduction in code complexity while being more
maintainable, performant, and aligned with business requirements.

Compare this to the equivalent LogicBank rules:

Rule.copy(derive=Item.unit_price, from_parent=Product.unit_price)
Rule.formula(derive=Item.amount, as_expression=lambda row: row.quantity * row.unit_price)
Rule.sum(derive=Order.amount_total, as_sum_of=Item.amount)
Rule.sum(derive=Customer.balance, as_sum_of=Order.amount_total, 
         where=lambda row: row.date_shipped is None)
Rule.constraint(validate=Customer, 
               as_condition=lambda row: row.balance <= row.credit_limit,
               error_msg="Customer balance exceeds credit limit")
"""
