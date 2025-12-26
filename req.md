# Odoo Stock Sync API Documentation

## Overview

This document describes all API endpoints for syncing and managing stock operations between Odoo and the external App system.

**Base URL:** `http://localhost:8069`

**Authentication:** All endpoints require an `Authorization` header with a valid token.

```
Authorization: your-token-here
```

---

## Table of Contents

1. [Authentication](#authentication)
2. [Sync Endpoints](#sync-endpoints)
   - [Sync Receipts](#1-sync-receipts)
   - [Sync Deliveries](#2-sync-deliveries)
   - [Sync Purchase Orders](#3-sync-purchase-orders)
3. [Action Endpoints](#action-endpoints)
   - [Receive Stock](#4-receive-stock)
   - [Deliver Stock](#5-deliver-stock)
   - [Receive Purchase Order](#6-receive-purchase-order)
4. [Error Codes Reference](#error-codes-reference)
5. [State Reference](#state-reference)

---

## Authentication

All API requests must include an `Authorization` header with a valid token.

### Token Validation
- Token is validated against `auth.user.token` model
- Token must not be expired (`token_expiration > current time`)

### Authentication Error Response
```json
{
    "error": "Unauthorized or token expired",
    "status": 401
}
```

**HTTP Status Code:** `401`

---

# Sync Endpoints

## 1. Sync Receipts

### Endpoint Details
| Property | Value |
|----------|-------|
| **URL** | `/api/sync/receipt` |
| **Method** | `GET` |
| **Auth** | Token Required |
| **Purpose** | Get all incoming stock receipts (excluding Purchase Order receipts) |

### What It Does
- Fetches all **incoming** stock pickings from the configured App warehouse
- **Excludes** receipts that originate from Purchase Orders (origin starting with `P0` or `PO`)
- Only returns pickings in `assigned` (ready) or `cancel` states
- Tracks changes since last sync

### Request
```bash
curl -X GET "http://localhost:8069/api/sync/receipt" \
  -H "Authorization: your-token-here"
```

### Success Response
**HTTP Status Code:** `200`

```json
{
    "success": true,
    "warehouse": {
        "id": 5,
        "name": "App"
    },
    "last_sync_time": "2025-12-26T10:00:00",
    "current_sync_time": "2025-12-26T12:00:00",
    "changes": {
        "created": [
            {
                "operation": 0,
                "type": 7,
                "model": "stock.picking",
                "ids": [45],
                "data": {
                    "id": 45,
                    "name": "App/IN/00001",
                    "state": "assigned",
                    "origin": null,
                    "scheduled_date": "2025-12-26T10:00:00",
                    "date_done": null,
                    "create_date": "2025-12-26T09:00:00",
                    "partner": {
                        "id": 10,
                        "name": "Supplier ABC",
                        "phone": "+966 50 123 4567",
                        "email": "supplier@example.com"
                    },
                    "warehouse_id": 5,
                    "warehouse_name": "App",
                    "picking_type_name": "Receipts",
                    "move_lines": [
                        {
                            "id": 101,
                            "product_id": 25,
                            "product_name": "Simple Pen",
                            "product_barcode": "123456789",
                            "product_code": "CONS_0002",
                            "quantity_ordered": 50.0,
                            "quantity_done": 0.0,
                            "quantity_remaining": 50.0,
                            "uom_id": 1,
                            "uom_name": "Units",
                            "state": "assigned"
                        }
                    ]
                }
            }
        ],
        "updated": [],
        "validated": [],
        "deleted": []
    },
    "summary": {
        "total_changes": 1,
        "created_count": 1,
        "updated_count": 0,
        "validated_count": 0,
        "deleted_count": 0
    }
}
```

### Error Responses

#### Sync App Not Configured
**HTTP Status Code:** `400`
```json
{
    "error": "Sync App not configured",
    "success": false
}
```

#### App Warehouse Not Configured
**HTTP Status Code:** `400`
```json
{
    "error": "App warehouse not configured",
    "success": false
}
```

#### Server Error
**HTTP Status Code:** `500`
```json
{
    "error": "Error message details",
    "success": false
}
```

### Business Logic
1. Validates authentication token
2. Retrieves sync configuration (`sync.app.config`)
3. Gets last sync timestamp from `sync.update` model
4. Queries `stock.picking` with filters:
   - Warehouse = App warehouse
   - Picking type = `incoming`
   - State IN (`assigned`, `cancel`)
   - Origin NOT LIKE `P0%` or `PO%` (excludes PO receipts)
5. Groups move lines by picking
6. Updates `last_transfer_sync` timestamp
7. Returns categorized changes

### Filtered States
| State | Included | Meaning |
|-------|----------|---------|
| `assigned` | ✅ Yes | Ready to receive |
| `cancel` | ✅ Yes | Cancelled |
| `done` | ❌ No | Already validated |
| `draft` | ❌ No | Not confirmed |
| `waiting` | ❌ No | Waiting for other operation |
| `confirmed` | ❌ No | Not ready (no stock reserved) |

---

## 2. Sync Deliveries

### Endpoint Details
| Property | Value |
|----------|-------|
| **URL** | `/api/sync/delivery` |
| **Method** | `GET` |
| **Auth** | Token Required |
| **Purpose** | Get all outgoing stock deliveries (includes all sources) |

### What It Does
- Fetches all **outgoing** stock pickings from the configured App warehouse
- **Includes** all deliveries (from Sales Orders, transfers, etc.)
- Only returns pickings in `assigned` (ready) or `cancel` states
- Tracks changes since last sync

### Request
```bash
curl -X GET "http://localhost:8069/api/sync/delivery" \
  -H "Authorization: your-token-here"
```

### Success Response
**HTTP Status Code:** `200`

```json
{
    "success": true,
    "warehouse": {
        "id": 5,
        "name": "App"
    },
    "last_sync_time": null,
    "current_sync_time": "2025-12-26T12:00:00",
    "changes": {
        "ready": [
            {
                "operation": 0,
                "type": 8,
                "model": "stock.picking",
                "ids": [50],
                "data": {
                    "id": 50,
                    "name": "App/OUT/00001",
                    "state": "assigned",
                    "origin": "S00015",
                    "scheduled_date": "2025-12-26T14:00:00",
                    "date_done": null,
                    "create_date": "2025-12-26T11:00:00",
                    "partner": {
                        "id": 15,
                        "name": "Customer XYZ",
                        "phone": "+966 55 999 1010",
                        "email": "customer@example.com"
                    },
                    "warehouse_id": 5,
                    "warehouse_name": "App",
                    "picking_type_name": "Delivery Orders",
                    "move_lines": [
                        {
                            "id": 120,
                            "product_id": 25,
                            "product_name": "Simple Pen",
                            "product_barcode": "123456789",
                            "product_code": "CONS_0002",
                            "quantity_ordered": 20.0,
                            "quantity_done": 0.0,
                            "quantity_remaining": 20.0,
                            "uom_id": 1,
                            "uom_name": "Units",
                            "state": "assigned"
                        }
                    ]
                }
            }
        ],
        "cancelled": []
    },
    "summary": {
        "total_changes": 1,
        "ready_count": 1,
        "cancelled_count": 0
    }
}
```

### Error Responses
Same as [Sync Receipts](#error-responses) errors.

### Business Logic
1. Validates authentication token
2. Retrieves sync configuration
3. Gets last sync timestamp (`last_delivery_sync`)
4. Queries `stock.picking` with filters:
   - Warehouse = App warehouse
   - Picking type = `outgoing`
   - State IN (`assigned`, `cancel`)
5. Groups move lines by picking
6. Updates `last_delivery_sync` timestamp
7. Returns categorized changes (`ready`, `cancelled`)

### Difference from Receipts
| Feature | Receipts | Deliveries |
|---------|----------|------------|
| Picking Type | `incoming` | `outgoing` |
| Origin Filter | Excludes PO | Includes all |
| Type Code | `7` | `8` |
| Response Keys | `created`, `updated`, `validated` | `ready`, `cancelled` |

---

## 3. Sync Purchase Orders

### Endpoint Details
| Property | Value |
|----------|-------|
| **URL** | `/api/sync/purchase-order` |
| **Method** | `GET` |
| **Auth** | Token Required |
| **Purpose** | Get all purchase orders from App warehouse |

### What It Does
- Fetches all confirmed purchase orders for the App warehouse
- Only returns POs in `purchase` or `cancel` states
- Includes order lines with product details
- Tracks changes since last sync

### Request
```bash
curl -X GET "http://localhost:8069/api/sync/purchase-order" \
  -H "Authorization: your-token-here"
```

### Success Response
**HTTP Status Code:** `200`

```json
{
    "success": true,
    "warehouse": {
        "id": 5,
        "name": "App"
    },
    "last_sync_time": null,
    "current_sync_time": "2025-12-26T12:00:00",
    "changes": {
        "created": [
            {
                "operation": 6,
                "type": 5,
                "model": "purchase.order",
                "ids": [12],
                "data": {
                    "order_id": 12,
                    "order_name": "P00012",
                    "order_state": "purchase",
                    "date_order": "2025-12-26T09:00:00",
                    "date_planned": "2025-12-27T09:00:00",
                    "amount_untaxed": 500.0,
                    "amount_tax": 75.0,
                    "amount_total": 575.0,
                    "notes": "",
                    "currency": {
                        "id": 1,
                        "name": "SAR"
                    },
                    "partner": {
                        "id": 20,
                        "name": "Supplier ABC",
                        "phone": "+966 50 123 4567",
                        "email": "supplier@example.com",
                        "vat": "300012345600003"
                    },
                    "picking_type": {
                        "id": 41,
                        "name": "Receipts",
                        "warehouse_id": 5,
                        "warehouse_name": "App"
                    },
                    "order_lines": [
                        {
                            "id": 25,
                            "product_id": 99,
                            "product_name": "Simple Pen",
                            "product_barcode": "123456789",
                            "product_code": "CONS_0002",
                            "quantity": 100.0,
                            "qty_received": 0.0,
                            "qty_to_receive": 100.0,
                            "price_unit": 5.0,
                            "price_subtotal": 500.0,
                            "uom_id": 1,
                            "uom_name": "Units"
                        }
                    ]
                }
            }
        ],
        "updated": [],
        "deleted": []
    },
    "summary": {
        "total_changes": 1,
        "created_count": 1,
        "updated_count": 0,
        "deleted_count": 0
    }
}
```

### Error Responses
Same as [Sync Receipts](#error-responses) errors.

### Business Logic
1. Validates authentication token
2. Retrieves sync configuration
3. Gets last sync timestamp (`last_receipt_sync`)
4. Queries `purchase.order` with filters:
   - Warehouse = App warehouse (via picking type)
   - State IN (`purchase`, `cancel`)
5. Groups order lines by purchase order
6. Updates `last_receipt_sync` timestamp
7. Returns categorized changes

---

# Action Endpoints

## 4. Receive Stock

### Endpoint Details
| Property | Value |
|----------|-------|
| **URL** | `/api/stock/receive` |
| **Method** | `POST` |
| **Auth** | Token Required |
| **Purpose** | Validate incoming stock receipt with quantities |

### What It Does
- Receives and validates an incoming stock picking
- **Allows** receiving MORE than ordered quantity (over-receiving)
- **Does NOT** create backorders for partial receipts
- Sets non-received lines to zero quantity
- Checks if origin transfer is cancelled

### Request
```bash
curl -X POST "http://localhost:8069/api/stock/receive" \
  -H "Authorization: your-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "picking_name": "App/IN/00001",
    "lines": [
        {
            "move_id": 101,
            "qty_received": 50.0
        },
        {
            "move_id": 102,
            "qty_received": 30.0
        }
    ]
}'
```

### Request Body
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `picking_name` | string | Yes | Stock picking reference (e.g., "App/IN/00001") |
| `lines` | array | Yes | Array of move lines to receive |
| `lines[].move_id` | integer | Yes | Stock move ID |
| `lines[].qty_received` | float | Yes | Quantity to receive |

### Success Response
**HTTP Status Code:** `200`

```json
{
    "status": "success",
    "message": "Stock picking App/IN/00001 validated successfully",
    "picking": {
        "id": 45,
        "name": "App/IN/00001",
        "state": "done",
        "date_done": "2025-12-26T12:30:00",
        "origin": null,
        "origin_state": null
    },
    "received_lines": [
        {
            "move_id": 101,
            "product_id": 25,
            "product_name": "Simple Pen",
            "product_barcode": "123456789",
            "qty_ordered": 50.0,
            "qty_received": 50.0,
            "is_over_receive": false,
            "over_qty": 0
        }
    ],
    "not_received_lines": [
        {
            "move_id": 103,
            "product_id": 26,
            "product_name": "Notebook",
            "product_barcode": "987654321",
            "qty_ordered": 20.0,
            "qty_received": 0,
            "is_over_receive": false,
            "over_qty": 0
        }
    ],
    "summary": {
        "total_lines": 2,
        "received_lines_count": 1,
        "not_received_lines_count": 1,
        "picking_validated": true,
        "has_over_receives": false,
        "over_receive_count": 0,
        "backorder_created": false
    },
    "warnings": {
        "message": "Some items were received in quantities greater than ordered",
        "over_received_items": [
            {
                "move_id": 101,
                "product_name": "Simple Pen",
                "ordered_qty": 50.0,
                "already_received": 0.0,
                "qty_to_receive": 60.0,
                "over_qty": 10.0
            }
        ]
    }
}
```

### Error Responses

#### Picking Not Found
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Stock picking App/IN/00999 not found"
}
```

#### Picking Already Validated
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Stock picking App/IN/00001 is already validated",
    "picking": {
        "id": 45,
        "name": "App/IN/00001",
        "state": "done",
        "date_done": "2025-12-26T10:00:00"
    }
}
```

#### Picking Cancelled
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Stock picking App/IN/00001 is cancelled"
}
```

#### Picking in Draft State
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Stock picking App/IN/00001 is in draft state. Please confirm it first."
}
```

#### Picking Waiting
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Stock picking App/IN/00001 is waiting for another operation"
}
```

#### Picking Not Ready
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Stock picking App/IN/00001 is confirmed but not ready (waiting for stock availability)"
}
```

#### Origin Transfer Cancelled
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Cannot receive: Origin transfer WH/OUT/00019 has been cancelled",
    "origin_picking": {
        "id": 39,
        "name": "WH/OUT/00019",
        "state": "cancel"
    }
}
```

#### Validation Errors
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Validation failed",
    "errors": [
        "Move 101: Invalid quantity 0 (must be greater than 0)",
        "Move 999: Not found in picking App/IN/00001"
    ]
}
```

#### Validation Failed (State Not Done)
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Failed to validate receipt App/IN/00001. Current state: assigned"
}
```

### Business Logic Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECEIVE STOCK FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. AUTHENTICATION                                              │
│     └── Validate token                                          │
│                                                                 │
│  2. FIND PICKING                                                │
│     └── Search by picking_name                                  │
│                                                                 │
│  3. STATE VALIDATION                                            │
│     ├── ❌ cancel → Error: "is cancelled"                       │
│     ├── ❌ done → Error: "is already validated"                 │
│     ├── ❌ draft → Error: "is in draft state"                   │
│     ├── ❌ waiting → Error: "is waiting"                        │
│     ├── ❌ confirmed → Error: "is not ready"                    │
│     └── ✅ assigned → Continue                                  │
│                                                                 │
│  4. CHECK ORIGIN (if exists)                                    │
│     └── If origin picking is cancelled → Error                  │
│                                                                 │
│  5. VALIDATE LINES                                              │
│     ├── qty_received <= 0 → Error                               │
│     ├── move_id not found → Error                               │
│     └── qty_received > ordered → Warning (allowed)              │
│                                                                 │
│  6. RESET ALL MOVES TO ZERO                                     │
│     └── Set quantity_done = 0 for all moves                     │
│                                                                 │
│  7. PROCESS RECEIVED LINES                                      │
│     └── Set quantity_done = qty_received                        │
│                                                                 │
│  8. VALIDATE PICKING (NO BACKORDER)                             │
│     ├── Use context: skip_backorder=True                        │
│     ├── Handle backorder wizard → process_cancel_backorder()    │
│     └── Handle immediate transfer wizard → process()            │
│                                                                 │
│  9. RETURN SUCCESS                                              │
│     └── Return validated picking details                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features
| Feature | Behavior |
|---------|----------|
| Over-receiving | ✅ Allowed (with warning) |
| Under-receiving | ✅ Allowed |
| Zero quantity | ❌ Blocked |
| Backorder creation | ❌ Disabled |
| Non-received lines | Set to 0 |

---

## 5. Deliver Stock

### Endpoint Details
| Property | Value |
|----------|-------|
| **URL** | `/api/stock/delivery` |
| **Method** | `POST` |
| **Auth** | Token Required |
| **Purpose** | Validate outgoing stock delivery with quantities |

### What It Does
- Delivers and validates an outgoing stock picking
- **Does NOT allow** delivering MORE than ordered quantity
- **Does NOT** create backorders for partial deliveries
- Sets non-delivered lines to zero quantity
- Checks if origin (Sale Order or transfer) is cancelled

### Request
```bash
curl -X POST "http://localhost:8069/api/stock/delivery" \
  -H "Authorization: your-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "picking_name": "App/OUT/00001",
    "lines": [
        {
            "move_id": 120,
            "qty_delivered": 20.0
        }
    ]
}'
```

### Request Body
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `picking_name` | string | Yes | Stock picking reference (e.g., "App/OUT/00001") |
| `lines` | array | Yes | Array of move lines to deliver |
| `lines[].move_id` | integer | Yes | Stock move ID |
| `lines[].qty_delivered` | float | Yes | Quantity to deliver |

### Success Response
**HTTP Status Code:** `200`

```json
{
    "status": "success",
    "message": "Stock picking App/OUT/00001 delivered successfully",
    "picking": {
        "id": 50,
        "name": "App/OUT/00001",
        "state": "done",
        "date_done": "2025-12-26T14:30:00",
        "origin": "S00015",
        "origin_state": "sale"
    },
    "delivered_lines": [
        {
            "move_id": 120,
            "product_id": 25,
            "product_name": "Simple Pen",
            "product_barcode": "123456789",
            "qty_ordered": 20.0,
            "qty_delivered": 20.0
        }
    ],
    "not_delivered_lines": [],
    "summary": {
        "total_lines": 1,
        "delivered_lines_count": 1,
        "not_delivered_lines_count": 0,
        "picking_validated": true,
        "backorder_created": false
    },
    "origin_order": {
        "id": 15,
        "name": "S00015",
        "state": "sale"
    }
}
```

### Error Responses

All error responses from [Receive Stock](#error-responses-3) apply, plus:

#### Not an Outgoing Delivery
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Stock picking App/IN/00001 is not an outgoing delivery"
}
```

#### Over-Delivery Blocked
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Validation failed",
    "errors": [
        "Move 120 (Simple Pen): Quantity to deliver (25) exceeds ordered quantity (20)"
    ]
}
```

#### Origin Sale Order Cancelled
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Cannot deliver: Origin sale order S00015 has been cancelled",
    "origin_order": {
        "id": 15,
        "name": "S00015",
        "state": "cancel"
    }
}
```

### Business Logic Flow
Same as Receive Stock, but with these differences:

| Step | Receive Stock | Deliver Stock |
|------|---------------|---------------|
| Picking Type Check | Not checked | Must be `outgoing` |
| Over-quantity | ✅ Allowed | ❌ Blocked |
| Origin Check | Checks picking | Checks Sale Order + picking |
| Response Field | `qty_received` | `qty_delivered` |

### Key Features
| Feature | Behavior |
|---------|----------|
| Over-delivering | ❌ Blocked (error) |
| Under-delivering | ✅ Allowed |
| Zero quantity | ❌ Blocked |
| Backorder creation | ❌ Disabled |
| Non-delivered lines | Set to 0 |

---

## 6. Receive Purchase Order

### Endpoint Details
| Property | Value |
|----------|-------|
| **URL** | `/api/purchase/receive` |
| **Method** | `POST` |
| **Auth** | Token Required |
| **Purpose** | Receive items from a Purchase Order |

### What It Does
- Receives items from a confirmed purchase order
- Validates quantities against remaining to receive
- Updates associated stock pickings
- Validates all pending pickings

### Request
```bash
curl -X POST "http://localhost:8069/api/purchase/receive" \
  -H "Authorization: your-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "po_name": "P00012",
    "lines": [
        {
            "line_id": 25,
            "qty_received": 100.0
        }
    ]
}'
```

### Request Body
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `po_name` | string | Yes | Purchase order reference (e.g., "P00012") |
| `lines` | array | Yes | Array of PO lines to receive |
| `lines[].line_id` | integer | Yes | Purchase order line ID |
| `lines[].qty_received` | float | Yes | Quantity to receive |

### Success Response
**HTTP Status Code:** `200`

```json
{
    "status": "success",
    "purchase_order": {
        "id": 12,
        "name": "P00012",
        "state": "purchase"
    },
    "received_lines": [
        {
            "line_id": 25,
            "product_id": 99,
            "product_name": "Simple Pen",
            "qty_received": 100.0,
            "picking_id": 55,
            "picking_name": "App/IN/00005"
        }
    ],
    "validated_pickings": [
        {
            "id": 55,
            "name": "App/IN/00005",
            "state": "done"
        }
    ]
}
```

### Error Responses

#### PO Not Found
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Purchase order P00999 not found"
}
```

#### PO Cancelled
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Purchase order P00012 is cancelled"
}
```

#### PO Not Confirmed
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Purchase order P00012 is not confirmed (current state: draft)"
}
```

#### No Receipt Found
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "No receipt found for this purchase order"
}
```

#### Already Validated
**HTTP Status Code:** `200`
```json
{
    "status": "success",
    "message": "Purchase order already validated",
    "purchase_order": {
        "id": 12,
        "name": "P00012",
        "state": "done"
    },
    "validated_pickings": [
        {
            "id": 55,
            "name": "App/IN/00005",
            "state": "done"
        }
    ]
}
```

#### Quantity Exceeds Remaining
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Validation failed",
    "errors": [
        "Line 25 (Simple Pen): Quantity to receive (150) exceeds remaining quantity (100)"
    ]
}
```

#### No Stock Move for Line
**HTTP Status Code:** `200`
```json
{
    "status": "error",
    "message": "Validation failed",
    "errors": [
        "Line 25 (Simple Pen): No stock move found for this line"
    ]
}
```

### Business Logic Flow

```
┌─────────────────────────────────────────────────────────────────┐
│              RECEIVE PURCHASE ORDER FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. AUTHENTICATION                                              │
│     └── Validate token                                          │
│                                                                 │
│  2. FIND PURCHASE ORDER                                         │
│     └── Search by po_name                                       │
│                                                                 │
│  3. STATE VALIDATION                                            │
│     ├── ❌ cancel → Error: "is cancelled"                       │
│     ├── ❌ draft/sent → Error: "is not confirmed"               │
│     └── ✅ purchase/done → Continue                             │
│                                                                 │
│  4. CHECK PICKINGS                                              │
│     ├── No pickings → Error: "No receipt found"                 │
│     └── All done → Success: "Already validated"                 │
│                                                                 │
│  5. VALIDATE LINES                                              │
│     ├── qty_received <= 0 → Error                               │
│     ├── line_id not found → Error                               │
│     ├── No stock move → Error                                   │
│     └── qty_received > remaining → Error                        │
│                                                                 │
│  6. PROCESS LINES                                               │
│     └── Update stock moves with quantity_done                   │
│                                                                 │
│  7. VALIDATE ALL PENDING PICKINGS                               │
│     └── Call _action_done() on each picking                     │
│                                                                 │
│  8. RETURN SUCCESS                                              │
│     └── Return PO, received lines, validated pickings           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features
| Feature | Behavior |
|---------|----------|
| Over-receiving | ❌ Blocked |
| Under-receiving | ✅ Allowed |
| Zero quantity | ❌ Blocked |
| Multiple pickings | ✅ Supported |

---

# Error Codes Reference

## HTTP Status Codes
| Code | Meaning |
|------|---------|
| `200` | Success (check `status` field for actual result) |
| `400` | Bad Request (configuration error) |
| `401` | Unauthorized (invalid/expired token) |
| `500` | Server Error |

## Status Field Values
| Value | Meaning |
|-------|---------|
| `"success"` | Operation completed successfully |
| `"error"` | Operation failed |

## Operation Codes (Sync)
| Code | Meaning |
|------|---------|
| `0` | Created / Ready |
| `1` | Updated |
| `2` | Cancelled |
| `3` | Validated |
| `6` | PO Created |
| `7` | PO Updated |

## Type Codes (Sync)
| Code | Model |
|------|-------|
| `5` | Purchase Order |
| `7` | Receipt (Incoming) |
| `8` | Delivery (Outgoing) |

---

# State Reference

## Stock Picking States
| State | Description | Can Receive/Deliver |
|-------|-------------|---------------------|
| `draft` | Draft | ❌ No |
| `waiting` | Waiting Another Operation | ❌ No |
| `confirmed` | Waiting (Not Reserved) | ❌ No |
| `assigned` | Ready | ✅ Yes |
| `done` | Done | ❌ No (Already done) |
| `cancel` | Cancelled | ❌ No |

## Purchase Order States
| State | Description | Can Receive |
|-------|-------------|-------------|
| `draft` | RFQ | ❌ No |
| `sent` | RFQ Sent | ❌ No |
| `to approve` | To Approve | ❌ No |
| `purchase` | Purchase Order | ✅ Yes |
| `done` | Locked | ✅ Yes (if pickings available) |
| `cancel` | Cancelled | ❌ No |

---

# Configuration Requirements

## Required Odoo Configuration

### 1. Sync App Config (`sync.app.config`)
```python
# Required fields:
app_warehouse_id = Many2one('stock.warehouse')  # App warehouse
```

### 2. Sync Update Tracker (`sync.update`)
```python
# Required fields:
last_transfer_sync = Datetime  # For receipts
last_delivery_sync = Datetime  # For deliveries
last_receipt_sync = Datetime   # For purchase orders
```

### 3. Auth User Token (`auth.user.token`)
```python
# Required fields:
token = Char
token_expiration = Datetime
```

---

# Testing Examples

## Test Sync Receipts
```bash
# First sync (no last_sync)
curl -X GET "http://localhost:8069/api/sync/receipt" \
  -H "Authorization: test-token-123"

# Expected: All assigned/cancel receipts from App warehouse
```

## Test Receive Stock
```bash
# Receive with valid quantities
curl -X POST "http://localhost:8069/api/stock/receive" \
  -H "Authorization: test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "picking_name": "App/IN/00001",
    "lines": [
        {"move_id": 101, "qty_received": 50.0}
    ]
}'

# Expected: Success response with validated picking
```

## Test Deliver Stock (Over-delivery blocked)
```bash
# Try to deliver more than ordered
curl -X POST "http://localhost:8069/api/stock/delivery" \
  -H "Authorization: test-token-123" \
  -H "Content-Type: application/json" \
  -d '{
    "picking_name": "App/OUT/00001",
    "lines": [
        {"move_id": 120, "qty_delivered": 999.0}
    ]
}'

# Expected: Error - "Quantity to deliver (999) exceeds ordered quantity (20)"
```

---

# Summary Table

| Endpoint | Method | Purpose | Over-Qty | Backorder |
|----------|--------|---------|----------|-----------|
| `/api/sync/receipt` | GET | Sync incoming receipts | N/A | N/A |
| `/api/sync/delivery` | GET | Sync outgoing deliveries | N/A | N/A |
| `/api/sync/purchase-order` | GET | Sync purchase orders | N/A | N/A |
| `/api/stock/receive` | POST | Receive incoming stock | ✅ Allowed | ❌ No |
| `/api/stock/delivery` | POST | Deliver outgoing stock | ❌ Blocked | ❌ No |
| `/api/purchase/receive` | POST | Receive PO items | ❌ Blocked | N/A |

---

**Document Version:** 1.0  
**Last Updated:** December 26, 2025  
**Author:** Development Team